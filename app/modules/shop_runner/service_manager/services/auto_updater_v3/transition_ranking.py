"""Cost-first UP: jump по upper states, rec-gate, worst-per-state imputation.

Два независимых сигнала (не путать):
- ``missing_target_matrix`` — нет валидной матрицы целевых мест M/O/C; стоимость из worst-per-state.
- ``missing_above_rec`` — ``above_rec_conversion is None``; на полке provisional rec-pass, tier ниже confirmed.

Сортировка: rec tier → state_cost → pay_for_order → keyword_id.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
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
    step_down,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_allows_up(hard_status: int) -> bool:
    """UP: авто (1) и белый список (2), как в ``rollout_planner``."""
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)

_PreparedEntry = tuple["KeywordV3Context", KeywordStrategyMode]
PreparedList = list[_PreparedEntry]


class RecTier(str, Enum):
    """Rec-уверенность для сортировки (полка)."""

    CONFIRMED = "confirmed"
    MISSING_ABOVE_REC = "missing_above_rec"
    NOT_APPLICABLE = "not_applicable"


class UpMoveKind(str, Enum):
    """Тип UP-перехода для логов."""

    OFF_TO_MIN = "off_to_min"
    OFF_TO_OPT = "off_to_opt"
    OFF_TO_MAX = "off_to_max"
    MIN_TO_OPT = "min_to_opt"
    MIN_TO_MAX = "min_to_max"
    OPT_TO_MAX = "opt_to_max"


@dataclass(frozen=True)
class TransitionCandidate:
    """Один допустимый UP-переход с метриками для ранжирования."""

    keyword_setting_id: int
    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode
    move_kind: UpMoveKind
    state_cost: float
    pay_for_order: float
    rec_tier: RecTier
    imputed: bool  # state_cost из worst-per-state при missing_target_matrix


def _catalog_for_ctx(ctx: "KeywordV3Context") -> dict[AggressionTargetMode, ModeCandidate]:
    return build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
    )


def missing_target_matrix(ctx: "KeywordV3Context") -> bool:
    """Нет ни одного валидного целевого места M/O/C в матрице профиля."""
    return not any(mc.is_valid for mc in _catalog_for_ctx(ctx).values())


def missing_above_rec(ctx: "KeywordV3Context") -> bool:
    """Нет подтверждённого rec-сигнала (``above_rec_conversion is None``)."""
    return ctx.keyword.above_rec_conversion is None


def upper_target_modes(current: KeywordStrategyMode) -> list[KeywordStrategyMode]:
    """Все режимы строго выше текущего (jump разрешён)."""
    cur = int(current)
    out: list[KeywordStrategyMode] = []
    for mode in (
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        if int(mode) > cur:
            out.append(mode)
    return out


def move_kind_for(
    from_mode: KeywordStrategyMode,
    to_mode: KeywordStrategyMode,
) -> UpMoveKind:
    pair = (from_mode, to_mode)
    mapping: dict[tuple[KeywordStrategyMode, KeywordStrategyMode], UpMoveKind] = {
        (KeywordStrategyMode.OFF, KeywordStrategyMode.MIN_CPA): UpMoveKind.OFF_TO_MIN,
        (KeywordStrategyMode.OFF, KeywordStrategyMode.OPTIMUM): UpMoveKind.OFF_TO_OPT,
        (
            KeywordStrategyMode.OFF,
            KeywordStrategyMode.MAX_CONVERSION,
        ): UpMoveKind.OFF_TO_MAX,
        (
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.OPTIMUM,
        ): UpMoveKind.MIN_TO_OPT,
        (
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.MAX_CONVERSION,
        ): UpMoveKind.MIN_TO_MAX,
        (
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.MAX_CONVERSION,
        ): UpMoveKind.OPT_TO_MAX,
    }
    return mapping[pair]


def _target_mode_for_strategy(mode: KeywordStrategyMode) -> AggressionTargetMode:
    return AggressionTargetMode[mode.name]


def _has_valid_target_place_data(
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> bool:
    return any(mc.is_valid for mc in catalog.values())


def _shelf_rec_filter_applies(click_mode: ShelfClickMode) -> bool:
    """Барьер «лучше полок» только при shelf >= organic (см. auto_updater_traffic_policy)."""
    return click_mode in (
        ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        ShelfClickMode.UNKNOWN,
    )


def passes_rec_gate_for_up(
    above_rec: bool | None,
    *,
    click_mode: ShelfClickMode,
) -> bool:
    """UP разрешён: organic — без rec-барьера; на полке — не ``above_rec=False``."""
    if not _shelf_rec_filter_applies(click_mode):
        return True
    return above_rec is not False


def _rec_tier_for_keyword(
    above_rec: bool | None,
    *,
    click_mode: ShelfClickMode,
) -> RecTier:
    if not _shelf_rec_filter_applies(click_mode):
        return RecTier.NOT_APPLICABLE
    if above_rec is True:
        return RecTier.CONFIRMED
    if above_rec is None:
        return RecTier.MISSING_ABOVE_REC
    return RecTier.NOT_APPLICABLE


def _resolve_state_cost(
    mc: ModeCandidate,
    target: AggressionTargetMode,
    worst_costs: dict[AggressionTargetMode, float],
    *,
    use_imputation: bool,
) -> tuple[float, bool]:
    if mc.is_valid and mc.predicted_cpa is not None:
        return float(mc.predicted_cpa), False
    if use_imputation:
        w = worst_costs.get(target)
        if w is not None:
            return w, True
    return float("inf"), False


def build_worst_per_state_costs(
    prepared: PreparedList,
) -> dict[AggressionTargetMode, float]:
    """Worst (max) predicted CPA per M/O/C среди ключей с валидной матрицей."""
    worst: dict[AggressionTargetMode, float] = {}
    for ctx, _mode in prepared:
        if missing_target_matrix(ctx):
            continue
        catalog = _catalog_for_ctx(ctx)
        if not _has_valid_target_place_data(catalog):
            continue
        for target in (
            AggressionTargetMode.MIN_CPA,
            AggressionTargetMode.OPTIMUM,
            AggressionTargetMode.MAX_CONVERSION,
        ):
            mc = catalog.get(target)
            if mc is None or not mc.is_valid or mc.predicted_cpa is None:
                continue
            cost = float(mc.predicted_cpa)
            prev = worst.get(target)
            if prev is None or cost > prev:
                worst[target] = cost
    return worst


def collect_transition_candidates(
    prepared: PreparedList,
    *,
    click_mode: ShelfClickMode,
) -> list[TransitionCandidate]:
    """Все допустимые UP-переходы с метриками (jump по upper states)."""
    worst_costs = build_worst_per_state_costs(prepared)
    out: list[TransitionCandidate] = []

    for ctx, current_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if current_mode == KeywordStrategyMode.MAX_CONVERSION:
            continue
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=click_mode,
        ):
            continue

        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue

        catalog = _catalog_for_ctx(ctx)
        use_matrix_imputation = missing_target_matrix(ctx)
        tier = _rec_tier_for_keyword(
            ctx.keyword.above_rec_conversion,
            click_mode=click_mode,
        )
        pfo = float(ctx.keyword.pay_for_order or 0.0)

        for to_mode in upper_target_modes(current_mode):
            target = _target_mode_for_strategy(to_mode)
            mc = catalog.get(target)
            if mc is None:
                continue
            cost, imputed = _resolve_state_cost(
                mc,
                target,
                worst_costs,
                use_imputation=use_matrix_imputation,
            )
            if cost == float("inf"):
                continue
            out.append(
                TransitionCandidate(
                    keyword_setting_id=ks_id,
                    from_mode=current_mode,
                    to_mode=to_mode,
                    move_kind=move_kind_for(current_mode, to_mode),
                    state_cost=cost,
                    pay_for_order=pfo,
                    rec_tier=tier,
                    imputed=imputed,
                )
            )
    return out


def _tier_sort_key(tier: RecTier) -> int:
    order = {
        RecTier.CONFIRMED: 0,
        RecTier.MISSING_ABOVE_REC: 1,
        RecTier.NOT_APPLICABLE: 2,
    }
    return order.get(tier, 3)


def _candidate_sort_key(c: TransitionCandidate) -> tuple[int, float, float, int]:
    return (
        _tier_sort_key(c.rec_tier),
        c.state_cost,
        c.pay_for_order,
        c.keyword_setting_id,
    )


def pick_one_up_cost_first(
    candidates: list[TransitionCandidate],
    *,
    reason_prefix: str,
) -> V3Action | None:
    """Один UP: минимальный state_cost, tie-break pay_for_order."""
    if not candidates:
        return None
    best = min(candidates, key=_candidate_sort_key)
    return _candidate_to_action(best, reason_prefix=reason_prefix)


def pick_one_up_layered(
    candidates: list[TransitionCandidate],
    *,
    aggressiveness: V3RolloutAggressiveness,
    reason_prefix: str,
) -> V3Action | None:
    """Слои OFF→MIN → MIN→OPT → OPT→MAX; внутри слоя — cost-first."""
    layer_order = (
        (UpMoveKind.OFF_TO_MIN,),
        (UpMoveKind.MIN_TO_OPT,),
        (UpMoveKind.OPT_TO_MAX,),
    )
    max_layer = min(int(aggressiveness), len(layer_order))
    for layer_idx in range(max_layer):
        kinds = layer_order[layer_idx]
        layer_cands = [c for c in candidates if c.move_kind in kinds]
        if not layer_cands:
            continue
        action = pick_one_up_cost_first(
            layer_cands,
            reason_prefix=f"{reason_prefix}_layer{layer_idx + 1}",
        )
        if action is not None:
            return action
    return None


def pick_one_up_piecewise_shelf(
    candidates: list[TransitionCandidate],
) -> V3Action | None:
    """Поштучная полка: OFF→MIN, затем MIN→OPT, затем OPT→MAX."""
    steps = (
        UpMoveKind.OFF_TO_MIN,
        UpMoveKind.MIN_TO_OPT,
        UpMoveKind.OPT_TO_MAX,
    )
    for kind in steps:
        step_cands = [c for c in candidates if c.move_kind == kind]
        if not step_cands:
            continue
        action = pick_one_up_cost_first(step_cands, reason_prefix="shelf_piecewise")
        if action is not None:
            return action
    return None


def _candidate_to_action(
    cand: TransitionCandidate,
    *,
    reason_prefix: str,
) -> V3Action:
    if cand.imputed:
        reason = "up_imputed_missing_target_matrix"
    elif cand.rec_tier == RecTier.MISSING_ABOVE_REC:
        reason = "up_missing_above_rec"
    else:
        reason = f"{reason_prefix}_cost_first"
    return V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=cand.keyword_setting_id,
        target_strategy_mode=cand.to_mode,
        reason=reason,
        selection_log=V3SelectionLog(
            pool_size=1,
            rec_tier=cand.rec_tier.value,
            state_cost=cand.state_cost,
            pay_for_order=cand.pay_for_order,
            from_mode=cand.from_mode.name,
            to_mode=cand.to_mode.name,
            move_kind=cand.move_kind.value,
            imputed=cand.imputed,
        ),
    )


def plan_shelf_rec_false_cleanup_down(
    prepared: PreparedList,
    *,
    click_mode: ShelfClickMode,
) -> list[V3Action] | None:
    """Полка: above_rec=False → один DOWN по самому дорогому активному."""
    if click_mode is not ShelfClickMode.SHELF_DOMINANT_OR_EQUAL:
        return None

    actives: list[tuple["KeywordV3Context", KeywordStrategyMode]] = []
    for ctx, mode in prepared:
        if mode == KeywordStrategyMode.OFF:
            continue
        if ctx.keyword.above_rec_conversion is not False:
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        actives.append((ctx, mode))

    if not actives:
        return None

    def sort_key(t: tuple["KeywordV3Context", KeywordStrategyMode]) -> float:
        return float(t[0].keyword.pay_for_order or 0.0)

    actives.sort(key=sort_key, reverse=True)
    ctx, mode = actives[0]
    nxt = step_down(mode)
    if nxt is None:
        return None
    ks_id = ctx.keyword.keyword_setting_original_id
    if ks_id is None:
        return None
    return [
        V3Action(
            action=V3ActionType.DOWN,
            keyword_setting_id=ks_id,
            reason="shelf_rec_false_cleanup",
        )
    ]


def plan_cost_first_up_one(
    prepared: PreparedList,
    *,
    click_mode: ShelfClickMode,
    layered: bool,
    aggressiveness: V3RolloutAggressiveness,
    piecewise_shelf: bool,
) -> list[V3Action]:
    """Один UP за цикл; выбор по transition_ranking."""
    candidates = collect_transition_candidates(prepared, click_mode=click_mode)
    if not candidates:
        return [
            V3Action(
                action=V3ActionType.DO_NOTHING,
                reason="no_valid_up_after_rec_filter",
            )
        ]

    if piecewise_shelf:
        action = pick_one_up_piecewise_shelf(candidates)
    elif layered:
        action = pick_one_up_layered(
            candidates,
            aggressiveness=aggressiveness,
            reason_prefix="layered",
        )
    else:
        action = pick_one_up_cost_first(candidates, reason_prefix="cost_first")

    if action is None:
        return [
            V3Action(
                action=V3ActionType.DO_NOTHING,
                reason="no_valid_up_in_layers",
            )
        ]
    return [action]
