"""RolloutPlanner: MIN→OPT→MAX — **послойная** стратегия (по уровню для всех).

Вне полочной фазы и при ``organic > shelf`` в полочной фазе: ``plan_rollout_underperform_one``
с ``strict`` слоями по ``aggressiveness``. Поштучная стратегия — в ``shelf_promotion_policy``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    step_down,
    step_up,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_allows_up(hard_status: int) -> bool:
    """UP (ladder): авто (1) и белый список (2)."""
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


# If more than this many OFF→MIN candidates exist, stay on strict MIN-first (level 2).
_LEVEL2_OFF_STRICT_ABOVE = 3
# Level 3: allow mixed pool unless this many OFF→MIN remain.
_LEVEL3_OFF_STRICT_ABOVE = 8


def _conv_sort_key(ctx: KeywordV3Context) -> float:
    return float(ctx.keyword.conv_views_to_orders)


def _down_sort_key(ctx: KeywordV3Context) -> tuple[float, float]:
    pfo = ctx.keyword.pay_for_order
    pay = float("-inf") if pfo is None else float(pfo)
    rating = ctx.keyword.rating or 0.0
    return (pay, rating)


def _active_entries(
    prepared: list[tuple[KeywordV3Context, KeywordStrategyMode, bool]],
) -> list[tuple[KeywordV3Context, KeywordStrategyMode, bool]]:
    return [(c, m, p) for c, m, p in prepared if m != KeywordStrategyMode.OFF]


def _off_entries(
    prepared: list[tuple[KeywordV3Context, KeywordStrategyMode, bool]],
) -> list[tuple[KeywordV3Context, KeywordStrategyMode, bool]]:
    return [(c, m, p) for c, m, p in prepared if m == KeywordStrategyMode.OFF]


def _strict_min_first(aggr: V3RolloutAggressiveness, off_with_min_count: int) -> bool:
    if aggr == V3RolloutAggressiveness.MIN:
        return True
    if aggr == V3RolloutAggressiveness.MID:
        return off_with_min_count > _LEVEL2_OFF_STRICT_ABOVE
    return off_with_min_count > _LEVEL3_OFF_STRICT_ABOVE


def _up_move_kind(
    mode: KeywordStrategyMode,
) -> str | None:
    if mode == KeywordStrategyMode.OFF:
        return "off_to_min"
    if mode == KeywordStrategyMode.MIN_CPA:
        return "min_to_opt"
    if mode == KeywordStrategyMode.OPTIMUM:
        return "opt_to_max"
    return None


def try_valid_rollout_up(
    ctx: KeywordV3Context,
    mode: KeywordStrategyMode,
    proven: bool,
) -> V3Action | None:
    if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
        return None

    if mode == KeywordStrategyMode.OFF:
        cand = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
        )
        min_c = cand.get(AggressionTargetMode.MIN_CPA)
        if min_c is None or not min_c.is_valid:
            return None
        return V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ctx.keyword.keyword_setting_original_id,
            reason="rollout_off_to_min",
        )

    if not proven:
        return None
    if mode == KeywordStrategyMode.MAX_CONVERSION:
        return None
    nxt = step_up(mode)
    if nxt is None:
        return None
    cand = build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
    )
    try:
        target = AggressionTargetMode[nxt.name]
    except KeyError:
        return None
    mc = cand.get(target)
    if mc is None or not mc.is_valid:
        logger.debug(
            "v3 skip UP kw=%s: invalid candidate for %s",
            ctx.keyword.text,
            target,
        )
        return None
    return V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=ctx.keyword.keyword_setting_original_id,
        reason="rollout_step_up",
    )


def plan_rollout_underperform_one(
    prepared: list[tuple[KeywordV3Context, KeywordStrategyMode, bool]],
    aggressiveness: V3RolloutAggressiveness,
) -> list[V3Action]:
    """Single UP per cycle; conv order; layer policy by aggressiveness."""
    offs = _off_entries(prepared)
    off_actions: list[tuple[KeywordV3Context, KeywordStrategyMode, bool, V3Action]] = []
    for ctx, mode, proven in offs:
        act = try_valid_rollout_up(ctx, mode, proven)
        if act is not None:
            off_actions.append((ctx, mode, proven, act))

    actives = _active_entries(prepared)
    active_actions: list[tuple[KeywordV3Context, KeywordStrategyMode, bool, V3Action]] = []
    for ctx, mode, proven in actives:
        if mode == KeywordStrategyMode.OFF:
            continue
        act = try_valid_rollout_up(ctx, mode, proven)
        if act is not None:
            active_actions.append((ctx, mode, proven, act))

    off_min_count = len(off_actions)
    strict = _strict_min_first(aggressiveness, off_min_count)

    pools: list[list[tuple[KeywordV3Context, KeywordStrategyMode, bool, V3Action]]] = []
    if strict:
        if off_actions:
            pools.append(off_actions)
        else:
            min_to_opt = [t for t in active_actions if _up_move_kind(t[1]) == "min_to_opt"]
            if min_to_opt:
                pools.append(min_to_opt)
            else:
                opt_to_max = [t for t in active_actions if _up_move_kind(t[1]) == "opt_to_max"]
                if opt_to_max:
                    pools.append(opt_to_max)
    else:
        merged = off_actions + active_actions
        if merged:
            pools.append(merged)

    if not pools or not pools[0]:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="underperform_no_up")]

    pool = pools[0]
    pool.sort(key=lambda t: _conv_sort_key(t[0]), reverse=True)
    _ctx, _mode, _p, action = pool[0]
    return [action]


def plan_rollout_down_one(
    prepared: list[tuple[KeywordV3Context, KeywordStrategyMode, bool]],
    *,
    reason: str,
) -> list[V3Action]:
    """Single DOWN: highest pay_for_order first (expensive → cheap)."""
    actives = _active_entries(prepared)
    actives.sort(key=lambda t: _down_sort_key(t[0]), reverse=True)
    for ctx, mode, _proven in actives:
        if int(ctx.keyword.hard_status) != _HARD_STATUS_WHITE_LIST:
            continue
        if mode == KeywordStrategyMode.OFF:
            continue
        nxt = step_down(mode)
        if nxt is None:
            continue
        cand = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
        )
        if nxt != KeywordStrategyMode.OFF:
            try:
                target = AggressionTargetMode[nxt.name]
            except KeyError:
                continue
            mc = cand.get(target)
            if mc is None or not mc.is_valid:
                logger.debug(
                    "v3 skip DOWN kw=%s: invalid candidate for %s",
                    ctx.keyword.text,
                    target,
                )
                continue
        return [
            V3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=ctx.keyword.keyword_setting_original_id,
                reason=reason,
            )
        ]
    return [V3Action(action=V3ActionType.DO_NOTHING, reason=f"{reason}_no_down")]
