"""Построение и ранжирование UP-переходов V3 (каталог M/O/C → upper states → min state_cost).

Заменяет conv-first / neighbor-only логику в ``rollout_planner`` и ``shelf_promotion_policy``.
DOWN остаётся в ``rollout_planner.plan_rollout_down_one`` (legacy по ``pay_for_order``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.auto_updater_traffic_policy import (
    ShelfTrafficInfluenceMode,
    resolve_shelf_traffic_influence_mode,
    shelf_conversion_filter_applies,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    V3Action,
    V3ActionType,
    V3SelectionLog,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)

_LEVEL2_OFF_STRICT_ABOVE = 3
_LEVEL3_OFF_STRICT_ABOVE = 8


def _strict_min_first(aggr: V3RolloutAggressiveness, off_to_min_count: int) -> bool:
    if aggr == V3RolloutAggressiveness.MIN:
        return True
    if aggr == V3RolloutAggressiveness.MID:
        return off_to_min_count > _LEVEL2_OFF_STRICT_ABOVE
    return off_to_min_count > _LEVEL3_OFF_STRICT_ABOVE

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2

_PreparedEntry = tuple["KeywordV3Context", KeywordStrategyMode, bool]
_PreparedList = list[_PreparedEntry]


class RecTier(str, Enum):
    """Приоритет ключа в UP-пуле при shelf-dominant."""

    CONFIRMED = "confirmed"
    PROVISIONAL_IMPUTED = "provisional_imputed"
    NOT_APPLICABLE = "not_applicable"


class UpMoveKind(str, Enum):
    """Целевой уровень перехода (включая jump)."""

    OFF_TO_MIN = "off_to_min"
    OFF_TO_OPT = "off_to_opt"
    OFF_TO_MAX = "off_to_max"
    MIN_TO_OPT = "min_to_opt"
    MIN_TO_MAX = "min_to_max"
    OPT_TO_MAX = "opt_to_max"


@dataclass(frozen=True)
class TransitionCandidate:
    """Один допустимый UP: ключ → целевой режим M/O/C."""

    ctx: KeywordV3Context
    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode
    move_kind: UpMoveKind
    state_cost: float
    rec_tier: RecTier
    shelf_pending: bool
    imputed: bool


def state_cost_from_candidate(mc: ModeCandidate) -> float | None:
    """Себестоимость целевого режима для ранжирования UP."""
    if mc.predicted_cpa is not None:
        return float(mc.predicted_cpa)
    return None


def _mode_to_target(mode: KeywordStrategyMode) -> AggressionTargetMode | None:
    try:
        return AggressionTargetMode[mode.name]
    except KeyError:
        return None


def upper_target_modes(current: KeywordStrategyMode) -> list[KeywordStrategyMode]:
    """Режимы M/O/C строго выше ``current`` на лестнице."""
    cur = mode_level(current)
    out: list[KeywordStrategyMode] = []
    for m in (
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        if mode_level(m) > cur:
            out.append(m)
    return out


def move_kind_for(
    from_mode: KeywordStrategyMode,
    to_mode: KeywordStrategyMode,
) -> UpMoveKind | None:
    """Код перехода для слоёв и логов."""
    key = (from_mode, to_mode)
    mapping: dict[tuple[KeywordStrategyMode, KeywordStrategyMode], UpMoveKind] = {
        (KeywordStrategyMode.OFF, KeywordStrategyMode.MIN_CPA): UpMoveKind.OFF_TO_MIN,
        (KeywordStrategyMode.OFF, KeywordStrategyMode.OPTIMUM): UpMoveKind.OFF_TO_OPT,
        (KeywordStrategyMode.OFF, KeywordStrategyMode.MAX_CONVERSION): UpMoveKind.OFF_TO_MAX,
        (KeywordStrategyMode.MIN_CPA, KeywordStrategyMode.OPTIMUM): UpMoveKind.MIN_TO_OPT,
        (KeywordStrategyMode.MIN_CPA, KeywordStrategyMode.MAX_CONVERSION): UpMoveKind.MIN_TO_MAX,
        (KeywordStrategyMode.OPTIMUM, KeywordStrategyMode.MAX_CONVERSION): UpMoveKind.OPT_TO_MAX,
    }
    return mapping.get(key)


def _hard_status_allows_up(hard_status: int) -> bool:
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def _is_shelf_pending_keyword(ctx: KeywordV3Context) -> bool:
    kw = ctx.keyword
    return (
        kw.above_rec_conversion is True
        and kw.hard_status == _HARD_STATUS_AUTO_MODE
        and kw.status == KeywordStatus.BAD
        and kw.reason != KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    )


def _rec_tier_for_keyword(
    above_rec: bool | None,
    *,
    traffic_mode: ShelfTrafficInfluenceMode,
) -> RecTier:
    if not shelf_conversion_filter_applies(traffic_mode):
        return RecTier.NOT_APPLICABLE
    if above_rec is True:
        return RecTier.CONFIRMED
    if above_rec is None:
        return RecTier.PROVISIONAL_IMPUTED
    return RecTier.CONFIRMED  # unreachable for UP when False filtered


def _blocks_shelf_up(
    above_rec: bool | None,
    *,
    traffic_mode: ShelfTrafficInfluenceMode,
) -> bool:
    if not shelf_conversion_filter_applies(traffic_mode):
        return False
    return above_rec is False


def build_worst_per_state_costs(
    prepared: _PreparedList,
) -> dict[AggressionTargetMode, float]:
    """Консервативные эталоны кампании: max ``state_cost`` по data-ключам с валидной точкой."""
    worst: dict[AggressionTargetMode, float] = {}
    for ctx, _mode, _proven in prepared:
        if ctx.keyword.above_rec_conversion is None:
            continue
        catalog = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
        )
        for target in AggressionTargetMode:
            mc = catalog.get(target)
            if mc is None or not mc.is_valid:
                continue
            cost = state_cost_from_candidate(mc)
            if cost is None:
                continue
            prev = worst.get(target)
            if prev is None or cost > prev:
                worst[target] = cost
    return worst


def _resolve_state_cost(
    mc: ModeCandidate,
    target: AggressionTargetMode,
    *,
    worst_costs: dict[AggressionTargetMode, float],
    use_imputation: bool,
) -> tuple[float | None, bool]:
    cost = state_cost_from_candidate(mc)
    if cost is not None:
        return cost, False
    if not use_imputation:
        return None, False
    imputed = worst_costs.get(target)
    if imputed is None:
        return None, False
    return imputed, True


def _has_valid_target_place_data(
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> bool:
    """Есть ли у ключа валидный target-place профиль хотя бы для одного режима."""
    return any(mc.is_valid for mc in catalog.values())


def collect_transition_candidates(
    prepared: _PreparedList,
    *,
    click_mode: ShelfClickMode,
) -> list[TransitionCandidate]:
    """Все допустимые UP-переходы по ключам (jump в любой upper target)."""
    traffic_mode = _traffic_mode_from_click_mode(click_mode)
    worst_costs = build_worst_per_state_costs(prepared)
    out: list[TransitionCandidate] = []

    for ctx, current_mode, proven in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if _blocks_shelf_up(ctx.keyword.above_rec_conversion, traffic_mode=traffic_mode):
            continue

        catalog = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
        )
        tier = _rec_tier_for_keyword(
            ctx.keyword.above_rec_conversion,
            traffic_mode=traffic_mode,
        )
        # No-data: либо нет shelf-сигнала (above_rec=None), либо нет валидных target-place данных.
        use_imputation = (
            tier == RecTier.PROVISIONAL_IMPUTED
            or not _has_valid_target_place_data(catalog)
        )

        for to_mode in upper_target_modes(current_mode):
            target = _mode_to_target(to_mode)
            if target is None:
                continue
            mc = catalog.get(target)
            if mc is None:
                continue

            # Ограничение unproven действует только при наличии данных; no-data идёт через imputation.
            if to_mode != KeywordStrategyMode.MIN_CPA and not proven and not use_imputation:
                continue

            if mc.is_valid:
                cost, imputed = _resolve_state_cost(
                    mc,
                    target,
                    worst_costs=worst_costs,
                    use_imputation=False,
                )
            elif use_imputation:
                cost, imputed = _resolve_state_cost(
                    mc,
                    target,
                    worst_costs=worst_costs,
                    use_imputation=True,
                )
            else:
                continue
            if cost is None:
                continue

            mk = move_kind_for(current_mode, to_mode)
            if mk is None:
                continue

            out.append(
                TransitionCandidate(
                    ctx=ctx,
                    from_mode=current_mode,
                    to_mode=to_mode,
                    move_kind=mk,
                    state_cost=cost,
                    rec_tier=tier,
                    shelf_pending=_is_shelf_pending_keyword(ctx),
                    imputed=imputed,
                )
            )
    return out


def _traffic_mode_from_click_mode(click_mode: ShelfClickMode) -> ShelfTrafficInfluenceMode:
    if click_mode == ShelfClickMode.ORGANIC_DOMINANT:
        return ShelfTrafficInfluenceMode.ORGANIC_DOMINANT
    if click_mode == ShelfClickMode.SHELF_DOMINANT_OR_EQUAL:
        return ShelfTrafficInfluenceMode.SHELF_DOMINANT
    return ShelfTrafficInfluenceMode.UNKNOWN


def _tier_sort_key(tier: RecTier) -> int:
    if tier == RecTier.CONFIRMED:
        return 0
    if tier == RecTier.PROVISIONAL_IMPUTED:
        return 1
    return 0


def _candidate_sort_key(c: TransitionCandidate) -> tuple[int, float, int]:
    return (
        _tier_sort_key(c.rec_tier),
        c.state_cost,
        int(c.ctx.keyword.keyword_setting_original_id or 0),
    )


def pick_one_up_layered(
    candidates: list[TransitionCandidate],
    aggressiveness: V3RolloutAggressiveness,
    *,
    pool_size: int | None = None,
    pool_size_after_rec: int | None = None,
) -> V3Action | None:
    """Послойный выбор: целевой уровень M → O → C, внутри слоя min ``state_cost``."""
    if not candidates:
        return None

    off_to_min_count = sum(
        1
        for c in candidates
        if c.from_mode == KeywordStrategyMode.OFF
        and c.to_mode == KeywordStrategyMode.MIN_CPA
    )
    strict = _strict_min_first(aggressiveness, off_to_min_count)

    pool_layers: list[int]
    if strict:
        if any(mode_level(c.to_mode) == 1 for c in candidates):
            pool_layers = [1]
        elif any(mode_level(c.to_mode) == 2 for c in candidates):
            pool_layers = [2]
        else:
            pool_layers = [3]
    else:
        pool_layers = [1, 2, 3]

    for layer in pool_layers:
        layer_pool = [c for c in candidates if mode_level(c.to_mode) == layer]
        if not layer_pool:
            continue
        layer_pool.sort(key=_candidate_sort_key)
        return _candidate_to_action(
            layer_pool[0],
            reason_prefix="layered_cost_first",
            pool_size=pool_size,
            pool_size_after_rec=pool_size_after_rec,
        )

    return None


def pick_one_up_piecewise(
    candidates: list[TransitionCandidate],
    *,
    prefer_shelf_pending: bool,
    pool_size: int | None = None,
    pool_size_after_rec: int | None = None,
) -> V3Action | None:
    """Поштучный пул: shelf pending → остальные; min ``state_cost``."""
    if not candidates:
        return None
    if prefer_shelf_pending:
        pending = [c for c in candidates if c.shelf_pending]
        if pending:
            pending.sort(key=_candidate_sort_key)
            return _candidate_to_action(
                pending[0],
                reason_prefix="piecewise_shelf",
                pool_size=pool_size,
                pool_size_after_rec=pool_size_after_rec,
            )
    rest = [c for c in candidates if not c.shelf_pending]
    if not rest:
        return None
    rest.sort(key=_candidate_sort_key)
    return _candidate_to_action(
        rest[0],
        reason_prefix="piecewise_non_shelf",
        pool_size=pool_size,
        pool_size_after_rec=pool_size_after_rec,
    )


def pick_one_up_cost_first(
    candidates: list[TransitionCandidate],
    *,
    reason_prefix: str = "cost_first",
    pool_size: int | None = None,
    pool_size_after_rec: int | None = None,
) -> V3Action | None:
    if not candidates:
        return None
    ranked = sorted(candidates, key=_candidate_sort_key)
    return _candidate_to_action(
        ranked[0],
        reason_prefix=reason_prefix,
        pool_size=pool_size,
        pool_size_after_rec=pool_size_after_rec,
    )


def _candidate_to_action(
    cand: TransitionCandidate,
    *,
    reason_prefix: str,
    pool_size: int | None = None,
    pool_size_after_rec: int | None = None,
) -> V3Action:
    reason = reason_prefix
    if cand.imputed:
        reason = "up_provisional_imputed_no_data"
    ks_id = cand.ctx.keyword.keyword_setting_original_id
    return V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=ks_id,
        target_strategy_mode=cand.to_mode,
        reason=reason,
        selection_log=V3SelectionLog(
            pool_size=pool_size,
            pool_size_after_rec=pool_size_after_rec,
            rec_tier=cand.rec_tier.value,
            state_cost=cand.state_cost,
            from_mode=cand.from_mode.name,
            to_mode=cand.to_mode.name,
            move_kind=cand.move_kind.value,
            imputed=cand.imputed,
        ),
    )


def plan_cost_first_up_one(
    prepared: _PreparedList,
    *,
    click_mode: ShelfClickMode,
    layered: bool,
    aggressiveness: V3RolloutAggressiveness,
    piecewise_shelf: bool,
) -> list[V3Action]:
    """Единая точка UP: сбор кандидатов + политика ранжирования."""
    pool_before = len(prepared)
    candidates = collect_transition_candidates(prepared, click_mode=click_mode)
    pool_after = len(candidates)
    if not candidates:
        logger.info(
            "v3_up: no_valid_up_after_rec_filter pool_before=%s pool_after=%s",
            pool_before,
            pool_after,
        )
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="no_valid_up_after_rec_filter")]

    action: V3Action | None
    if piecewise_shelf:
        action = pick_one_up_piecewise(
            candidates,
            prefer_shelf_pending=True,
            pool_size=pool_before,
            pool_size_after_rec=pool_after,
        )
    elif layered:
        action = pick_one_up_layered(
            candidates,
            aggressiveness,
            pool_size=pool_before,
            pool_size_after_rec=pool_after,
        )
    else:
        action = pick_one_up_cost_first(
            candidates,
            pool_size=pool_before,
            pool_size_after_rec=pool_after,
        )

    if action is None:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="underperform_no_up")]
    return [action]


def plan_shelf_rec_false_cleanup_down(
    prepared: _PreparedList,
    *,
    click_mode: ShelfClickMode,
) -> list[V3Action] | None:
    """Clean-up: активные ключи с ``above_rec_conversion is False`` (shelf-dominant)."""
    traffic_mode = _traffic_mode_from_click_mode(click_mode)
    if not shelf_conversion_filter_applies(traffic_mode):
        return None

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
        plan_rollout_down_one,
    )

    false_actives = [
        (ctx, mode, proven)
        for ctx, mode, proven in prepared
        if mode != KeywordStrategyMode.OFF
        and ctx.keyword.above_rec_conversion is False
        and int(ctx.keyword.hard_status) == _HARD_STATUS_WHITE_LIST
    ]
    if not false_actives:
        return None
    actions = plan_rollout_down_one(false_actives, reason="shelf_rec_false_cleanup")
    if actions[0].action == V3ActionType.DOWN:
        return actions
    return None
