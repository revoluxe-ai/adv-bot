"""RolloutPlanner для non-shelf: pooled выбор UP с ограничением по aggressiveness.

Вне полочной фазы ``UNDERPERFORM`` использует единый планировщик переходов вверх:
из всех ``to_mode > current`` выбирается самый дешевый кандидат после фильтра
по максимальному target-состоянию (``aggressiveness`` 1/2/3).

При ``SalesStates.OVERSPEND`` (факт кампании выше ``max_pay_for_order``): сначала
``plan_overspend_force_off_over_max`` — все активные ключи с ``pay_for_order > max`` сразу в OFF;
если таких нет — один шаг ``plan_rollout_down_one``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    resolve_effective_state_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    V3Action,
    V3ActionType,
    V3SelectionLog,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    candidate_for_strategy_mode,
    count_effective_aggression_steps_between,
    count_effective_released_aggression_steps,
    iter_effective_upper_mode_groups,
    log_skipped_aliases,
    logical_modes_at_target_place_above,
    mode_candidates_same_effective_target,
    resolve_next_effective_step_down,
    resolve_next_effective_step_up,
    target_place_from_mode_candidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    UpdateContext,
    update_context_from_prepared,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager import (
    StepCandidate,
    StepManager,
    bump_prepared_list_only,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    effective_conv_for_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
    rec_gate_allows_up,
    state_rec_gate_status_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
    collect_transition_candidates,
    missing_target_matrix_from_catalog,
    move_kind_for,
    plan_one_up_by_policy,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_allows_up(hard_status: int) -> bool:
    """UP (ladder): авто (1) и белый список (2)."""
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def ladder_inputs_for_prepared(
    prepared: PreparedList,
    ladder_inputs: "LadderInputs | None" = None,
) -> "LadderInputs":
    """Единый ``LadderInputs`` на проход planner; worst только в ``ladder_inputs.worst_costs``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs as _LadderInputs,
    )

    if ladder_inputs is not None:
        return ladder_inputs
    return _LadderInputs.from_contexts([ctx for ctx, _ in prepared])


# If more than this many OFF→MIN candidates exist, stay on strict MIN-first (level 2).
_LEVEL2_OFF_STRICT_ABOVE = 3
# Level 3: allow mixed pool unless this many OFF→MIN remain.
_LEVEL3_OFF_STRICT_ABOVE = 8


def _mode_catalog_for_ctx(
    ctx: "KeywordV3Context",
    prepared: PreparedList | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """M/O/C state candidates; delegates to ``state_candidates_by_mode_for_ctx`` when ladder set."""
    if ladder_inputs is not None:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
            state_candidates_by_mode_for_ctx,
        )

        return state_candidates_by_mode_for_ctx(ctx, ladder_inputs)
    conv = _conv_for_ctx(ctx, prepared)
    rk = None
    return build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
        conv_views_to_orders=conv,
        rk_orders_per_cart=rk,
    )


def _conv_for_ctx(
    ctx: "KeywordV3Context",
    prepared: PreparedList | None = None,
) -> float:
    """Conv для кандидатов M/O/C: своя или импутация РК (см. ``keyword_v3_decision_data``)."""
    peer = [c for c, _ in prepared] if prepared else [ctx]
    eff = effective_conv_for_v3(ctx, peer)
    if eff is not None:
        return eff
    return float(ctx.keyword.conv_views_to_orders)


def _conv_sort_key(ctx: KeywordV3Context) -> float:
    return float(ctx.keyword.conv_views_to_orders)


def _down_sort_key(ctx: KeywordV3Context) -> tuple[float, float]:
    pfo = ctx.keyword.pay_for_order
    pay = float("-inf") if pfo is None else float(pfo)
    rating = ctx.keyword.rating or 0.0
    return (pay, rating)


def _active_entries(prepared: PreparedList) -> PreparedList:
    return [(c, m) for c, m in prepared if m != KeywordStrategyMode.OFF]


def _off_entries(prepared: PreparedList) -> PreparedList:
    return [(c, m) for c, m in prepared if m == KeywordStrategyMode.OFF]


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
    *,
    prepared: PreparedList | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> V3Action | None:
    if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
        return None

    conv = _conv_for_ctx(ctx, prepared)
    opc = (
        ladder_inputs.orders_per_cart_for_ctx(ctx) if ladder_inputs is not None else None
    )
    if mode == KeywordStrategyMode.OFF:
        cand = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
            conv_views_to_orders=conv if opc is None else None,
            orders_per_cart=opc,
        )
        min_c = cand.get(AggressionTargetMode.MIN_CPA)
        if min_c is None or not min_c.is_valid:
            return None
        return V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ctx.keyword.keyword_setting_original_id,
            reason="rollout_off_to_min",
        )

    if mode == KeywordStrategyMode.MAX_CONVERSION:
        return None
    catalog = _mode_catalog_for_ctx(ctx, prepared, ladder_inputs)
    step = resolve_next_effective_step_up(mode, catalog)
    log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
    nxt = step.next_mode
    if nxt is None:
        return None
    try:
        target = AggressionTargetMode[nxt.name]
    except KeyError:
        return None
    mc = catalog.get(target)
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
    prepared: PreparedList,
    aggressiveness: V3RolloutAggressiveness,
) -> list[V3Action]:
    """Single UP per cycle with pooled ranking and aggressiveness target cap."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=aggressiveness,
    )
    return plan_one_up_by_policy(prepared, policy=policy)


def keyword_pay_for_order_exceeds(
    ctx: "KeywordV3Context",
    *,
    ceiling: float,
) -> bool:
    """True, если ``keyword.pay_for_order`` (как в UI) строго выше ``ceiling``.

    Для tier ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV`` — основной критерий FORCE_OFF при
    OVERSPEND/trim (нет CH ``state_cost``; imputed conv не используется).
    """
    pfo = ctx.keyword.pay_for_order
    if pfo is None:
        return False
    return float(pfo) > float(ceiling)


def keyword_pay_for_order_exceeds_max(
    ctx: "KeywordV3Context",
    *,
    max_pay_for_order: float,
) -> bool:
    """True, если ``keyword.pay_for_order`` строго выше ``plan.max_pay_for_order``."""
    return keyword_pay_for_order_exceeds(ctx, ceiling=max_pay_for_order)


def plan_overspend_force_off_over_max(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    reason: str = "overspend_max_pfo",
) -> list[V3Action]:
    """Массовый сброс в OFF: активные ключи с себестоимостью выше ``max_pay_for_order``.

    Args:
        prepared: Контексты ключей с текущим ``strategy_mode``.
        max_pay_for_order: Плановый максимальный себес заказа (руб.).
        reason: Код причины в логах/applier.

    Returns:
        Список ``FORCE_OFF`` (может быть пустым).
    """
    actions: list[V3Action] = []
    for ctx, mode in prepared:
        if mode == KeywordStrategyMode.OFF:
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not keyword_pay_for_order_exceeds_max(
            ctx, max_pay_for_order=max_pay_for_order
        ):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        actions.append(
            V3Action(
                action=V3ActionType.FORCE_OFF,
                keyword_setting_id=ks_id,
                reason=reason,
            )
        )
    return actions


def plan_overspend_actions(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """OVERSPEND: массовый OFF по ключам выше max, иначе один DOWN."""
    forced = plan_overspend_force_off_over_max(
        prepared, max_pay_for_order=max_pay_for_order
    )
    if forced:
        return forced
    return plan_rollout_down_one(
        prepared, reason="overspend", ladder_inputs=ladder_inputs
    )


def _trim_state_cost_for_mode(
    ctx: "KeywordV3Context",
    mode: KeywordStrategyMode,
    *,
    current: KeywordStrategyMode,
    ladder_inputs: "LadderInputs",
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> tuple[float, bool]:
    """Себестоимость режима для trim/guard; для **текущего** режима — не ниже CPO на ``target_place``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        operational_cpo_at_keyword_target_place,
    )

    cost, imputed = resolve_effective_state_cost_for_mode(
        ctx=ctx,
        to_mode=mode,
        ladder_inputs=ladder_inputs,
        eligibility_by_ks_id=eligibility_by_ks_id,
    )
    if mode != current:
        return cost, imputed
    operational = operational_cpo_at_keyword_target_place(ctx, ladder_inputs=ladder_inputs)
    if operational is None:
        return cost, imputed
    if cost == float("inf"):
        return float(operational), imputed
    return max(float(cost), float(operational)), imputed


def should_skip_trim_for_same_effective_target(
    *,
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    trim_target: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
    cost_ceiling: float,
    ladder_inputs: "LadderInputs",
) -> bool:
    """Совпадает ли trim-skip «тот же target_place», что в ``_plan_trim_by_cost_ceiling``.

    True только если режимы ведут в одну точку каталога **и** операционный CPO на
    ``keyword.target_place`` отсутствует или ``<= cost_ceiling``. При CPO выше ceiling
    live guard **не** пропускает trim (режим меняется, ставка может остаться на месте).
    """
    if trim_target == current:
        return False
    current_c = candidate_for_strategy_mode(current, catalog)
    target_c = candidate_for_strategy_mode(trim_target, catalog)
    if not mode_candidates_same_effective_target(current_c, target_c):
        return False
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        operational_cpo_at_keyword_target_place,
    )

    operational = operational_cpo_at_keyword_target_place(
        ctx, ladder_inputs=ladder_inputs
    )
    return operational is None or float(operational) <= float(cost_ceiling)


def _fallback_min_instead_of_off_trim(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    cost_ceiling: float,
    ladder_inputs: "LadderInputs",
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> KeywordStrategyMode | None:
    """Если effective DOWN ушёл в OFF, но MIN по CPO проходит ceiling — trim в MIN (WL O=M)."""
    if current == KeywordStrategyMode.MIN_CPA:
        return None
    min_cost, _ = _trim_state_cost_for_mode(
        ctx,
        KeywordStrategyMode.MIN_CPA,
        current=current,
        ladder_inputs=ladder_inputs,
        eligibility_by_ks_id=eligibility_by_ks_id,
    )
    if min_cost != float("inf") and min_cost <= cost_ceiling:
        return KeywordStrategyMode.MIN_CPA
    return None


def _find_trim_target_mode(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    catalog: dict[AggressionTargetMode, ModeCandidate],
    cost_ceiling: float,
    ladder_inputs: "LadderInputs",
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> KeywordStrategyMode:
    """Ближайший режим ≤ current, где ``state_cost <= cost_ceiling``; иначе OFF."""
    mode = current
    while True:
        if mode == KeywordStrategyMode.OFF:
            return KeywordStrategyMode.OFF
        if mode_level(mode) > mode_level(policy.max_target_mode):
            step = resolve_next_effective_step_down(mode, catalog)
            log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
            if step.next_mode is None:
                return KeywordStrategyMode.OFF
            mode = step.next_mode
            continue
        cost, _ = _trim_state_cost_for_mode(
            ctx,
            mode,
            current=current,
            ladder_inputs=ladder_inputs,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if cost != float("inf") and cost <= cost_ceiling:
            return mode
        step = resolve_next_effective_step_down(mode, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        if step.next_mode is None:
            fb = _fallback_min_instead_of_off_trim(
                ctx,
                current,
                cost_ceiling=cost_ceiling,
                ladder_inputs=ladder_inputs,
                eligibility_by_ks_id=eligibility_by_ks_id,
            )
            return fb if fb is not None else KeywordStrategyMode.OFF
        if step.next_mode == KeywordStrategyMode.OFF:
            fb = _fallback_min_instead_of_off_trim(
                ctx,
                current,
                cost_ceiling=cost_ceiling,
                ladder_inputs=ladder_inputs,
                eligibility_by_ks_id=eligibility_by_ks_id,
            )
            if fb is not None:
                return fb
            return KeywordStrategyMode.OFF
        mode = step.next_mode


def _find_trim_target_mode_limited_steps(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    catalog: dict[AggressionTargetMode, ModeCandidate],
    cost_ceiling: float,
    ladder_inputs: "LadderInputs",
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    max_effective_steps: int,
) -> KeywordStrategyMode:
    """Не более ``max_effective_steps`` effective DOWN; stop early if ``state_cost <= ceiling``."""
    mode = current
    used = 0
    step_budget = max(1, int(max_effective_steps))
    while True:
        if mode == KeywordStrategyMode.OFF:
            return KeywordStrategyMode.OFF
        if mode_level(mode) > mode_level(policy.max_target_mode):
            if used >= step_budget:
                return mode
            step = resolve_next_effective_step_down(mode, catalog)
            log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
            if step.next_mode is None:
                return KeywordStrategyMode.OFF
            released = count_effective_released_aggression_steps(
                mode, step.next_mode, catalog
            )
            if released > 0:
                used += released
            mode = step.next_mode
            continue
        cost, _ = _trim_state_cost_for_mode(
            ctx,
            mode,
            current=current,
            ladder_inputs=ladder_inputs,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if cost != float("inf") and cost <= cost_ceiling:
            return mode
        if used >= step_budget:
            return mode
        step = resolve_next_effective_step_down(mode, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        if step.next_mode is None:
            fb = _fallback_min_instead_of_off_trim(
                ctx,
                current,
                cost_ceiling=cost_ceiling,
                ladder_inputs=ladder_inputs,
                eligibility_by_ks_id=eligibility_by_ks_id,
            )
            return fb if fb is not None else KeywordStrategyMode.OFF
        if step.next_mode == KeywordStrategyMode.OFF:
            fb = _fallback_min_instead_of_off_trim(
                ctx,
                current,
                cost_ceiling=cost_ceiling,
                ladder_inputs=ladder_inputs,
                eligibility_by_ks_id=eligibility_by_ks_id,
            )
            if fb is not None:
                return fb
            return KeywordStrategyMode.OFF
        released = count_effective_released_aggression_steps(
            mode, step.next_mode, catalog
        )
        if released > 0:
            used += released
        mode = step.next_mode


def _find_boost_target_mode_limited_steps(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    catalog: dict[AggressionTargetMode, ModeCandidate],
    cost_ceiling: float,
    ladder_inputs: "LadderInputs",
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    max_effective_steps: int,
) -> KeywordStrategyMode:
    """Не более ``max_effective_steps`` effective UP; stop если ``state_cost > ceiling``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        can_target_mode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
        rec_gate_allows_up,
        state_rec_gate_status_for_mode,
    )

    mode = current
    used = 0
    step_budget = max(1, int(max_effective_steps))
    elig = _eligibility_for_ctx(ctx, eligibility_by_ks_id)
    while True:
        if mode_level(mode) >= mode_level(policy.max_target_mode):
            return mode
        step = resolve_next_effective_step_up(mode, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        if step.next_mode is None:
            return mode
        candidate_mode = step.next_mode
        if elig is not None and not can_target_mode(elig, candidate_mode):
            return mode
        gate_status = state_rec_gate_status_for_mode(
            catalog,
            candidate_mode,
            policy,
            rec_orders_per_view=ladder_inputs.rec_orders_per_view,
            orders_per_cart=ladder_inputs.orders_per_cart_for_ctx(ctx),
        )
        if not rec_gate_allows_up(gate_status):
            return mode
        next_cost, _ = _trim_state_cost_for_mode(
            ctx,
            candidate_mode,
            current=current,
            ladder_inputs=ladder_inputs,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if next_cost == float("inf") or next_cost > cost_ceiling:
            return mode
        gained = count_effective_aggression_steps_between(
            mode, candidate_mode, catalog
        )
        if gained > 0:
            used += gained
        mode = candidate_mode
        if used >= step_budget:
            return mode


def _bump_prepared_mode(
    prepared: PreparedList,
    keyword_setting_id: int,
    new_mode: KeywordStrategyMode,
) -> PreparedList:
    """Re-export: bump ``active_mode`` без history (legacy)."""
    return bump_prepared_list_only(prepared, keyword_setting_id, new_mode)


def _hard_status_for_ks(prepared: PreparedList, keyword_setting_id: int) -> int:
    for ctx, _mode in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is not None and int(ks_id) == keyword_setting_id:
            return int(ctx.keyword.hard_status)
    return _HARD_STATUS_AUTO_MODE


def _append_trim_to_mode(
    actions: list[V3Action],
    *,
    ks_id: int,
    current: KeywordStrategyMode,
    target: KeywordStrategyMode,
    hard_status: int,
    reason: str = "trim_max_state_cost",
) -> None:
    """WL: DOWN; авто: FORCE_OFF (+ UP до целевого режима, если не OFF)."""
    if target == KeywordStrategyMode.OFF:
        actions.append(
            V3Action(
                action=V3ActionType.FORCE_OFF,
                keyword_setting_id=ks_id,
                reason=reason,
            )
        )
        return
    if int(hard_status) == _HARD_STATUS_WHITE_LIST:
        actions.append(
            V3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=ks_id,
                target_strategy_mode=target,
                reason=reason,
            )
        )
        return
    actions.append(
        V3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=ks_id,
            reason=reason,
        )
    )
    actions.append(
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ks_id,
            target_strategy_mode=target,
            reason=reason,
        )
    )


def _plan_trim_by_cost_ceiling(
    prepared: PreparedList,
    *,
    cost_ceiling: float,
    trim_reason: str,
    shelf_click_mode: "ShelfClickMode",
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
    max_effective_steps: int | None = None,
) -> list[V3Action]:
    """Снизить режим до ``state_cost <= cost_ceiling``.

    ``max_effective_steps=None`` — full trim (guard/max). Иначе — limited DOWN
    (calibration).
    """
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    actions: list[V3Action] = []
    for ctx, current in prepared:
        if current == KeywordStrategyMode.OFF:
            continue
        hard_status = int(ctx.keyword.hard_status)
        if hard_status not in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = _eligibility_for_ctx(ctx, eligibility_by_ks_id)
        if _min_cpa_bound_by_pay_for_order(elig):
            if keyword_pay_for_order_exceeds(
                ctx, ceiling=float(cost_ceiling)
            ):
                _append_trim_to_mode(
                    actions,
                    ks_id=ks_id,
                    current=current,
                    target=KeywordStrategyMode.OFF,
                    hard_status=hard_status,
                    reason=trim_reason,
                )
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        if max_effective_steps is None:
            target = _find_trim_target_mode(
                ctx,
                current,
                catalog=catalog,
                cost_ceiling=float(cost_ceiling),
                ladder_inputs=ladder,
                policy=policy,
                eligibility_by_ks_id=eligibility_by_ks_id,
            )
        else:
            target = _find_trim_target_mode_limited_steps(
                ctx,
                current,
                catalog=catalog,
                cost_ceiling=float(cost_ceiling),
                ladder_inputs=ladder,
                policy=policy,
                eligibility_by_ks_id=eligibility_by_ks_id,
                max_effective_steps=max_effective_steps,
            )
        skip_reasons: list[str] = []
        if target == current:
            skip_reasons.append("trim_target_eq_current")
        if should_skip_trim_for_same_effective_target(
            ctx=ctx,
            current=current,
            trim_target=target,
            catalog=catalog,
            cost_ceiling=float(cost_ceiling),
            ladder_inputs=ladder,
        ):
            skip_reasons.append("same_target_place")
            logger.debug(
                "v3 skip trim kw=%s: %s and %s same target_place",
                ctx.keyword.text,
                current.name,
                target.name,
            )
        if not skip_reasons and target != current:
            _append_trim_to_mode(
                actions,
                ks_id=ks_id,
                current=current,
                target=target,
                hard_status=hard_status,
                reason=trim_reason,
            )
    return actions


def plan_campaign_trim_by_max_state_cost(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    shelf_click_mode: "ShelfClickMode",
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """Снизить режим до ближайшего с ``state_cost <= plan.max_pay_for_order`` (не resolve).

    Вызывается из orchestrator, когда ``fact.pay_for_order > plan.max_pay_for_order``.
    """
    return _plan_trim_by_cost_ceiling(
        prepared,
        cost_ceiling=float(max_pay_for_order),
        trim_reason="trim_max_state_cost",
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
    )


def plan_resolve_calibration_trim(
    prepared: PreparedList,
    *,
    resolve: float,
    shelf_click_mode: "ShelfClickMode",
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
    max_effective_steps: int = 1,
) -> list[V3Action]:
    """Legacy alias: CAL DOWN через ``calibration_runner`` (для unit-тестов trim)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.calibration_runner import (
        plan_calibration_trim_actions,
    )

    return plan_calibration_trim_actions(
        prepared,
        resolve=resolve,
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
        max_effective_steps=max_effective_steps,
    )


def plan_rollout_down_one(
    prepared: PreparedList,
    *,
    reason: str,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """Single DOWN: highest pay_for_order first (expensive → cheap).

    Каталог M/O/C строится с ``ladder_inputs.rk_orders_per_cart`` (RK CPO), как в
    ``plan_max_cpa_guard`` / ``try_valid_rollout_up`` — не legacy conv-only.
    """
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    actives = _active_entries(prepared)
    actives.sort(key=lambda t: _down_sort_key(t[0]), reverse=True)
    for ctx, mode in actives:
        if int(ctx.keyword.hard_status) != _HARD_STATUS_WHITE_LIST:
            continue
        if mode == KeywordStrategyMode.OFF:
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        step = resolve_next_effective_step_down(mode, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        nxt = step.next_mode
        if nxt is None:
            continue
        if nxt != KeywordStrategyMode.OFF:
            try:
                target = AggressionTargetMode[nxt.name]
            except KeyError:
                continue
            mc = catalog.get(target)
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
                target_strategy_mode=nxt,
                reason=reason,
            )
        ]
    return [V3Action(action=V3ActionType.DO_NOTHING, reason=f"{reason}_no_down")]


@dataclass(frozen=True)
class _StateView:
    """Проекция состояния с расчётной стоимостью для rebalance-прохода."""

    ks_id: int
    strategy_mode: KeywordStrategyMode
    cost: float
    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode
    imputed: bool


def compute_resolve_cost_threshold(plan: PlanData, fact: FactData) -> float:
    """Вернуть текущий resolve порог: target при выполнении плана, иначе max."""
    if float(fact.predict_orders) >= float(plan.orders):
        return float(plan.target_pay_for_order)
    return float(plan.max_pay_for_order)


def is_resolve_valid(plan: PlanData, resolve: float) -> bool:
    """Проверить, что порог пригоден для state-решений."""
    return float(plan.max_pay_for_order) > 0 and float(resolve) > 0


def _eligibility_for_ctx(
    ctx: "KeywordV3Context",
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None,
    *,
    eligibility: "KeywordV3Eligibility | None" = None,
) -> "KeywordV3Eligibility | None":
    """Eligibility ключа из явного аргумента или map по ``keyword_setting_original_id``."""
    if eligibility is not None:
        return eligibility
    if eligibility_by_ks_id is None:
        return None
    ks_id = ctx.keyword.keyword_setting_original_id
    if ks_id is None:
        return None
    return eligibility_by_ks_id.get(int(ks_id))


def _resolve_state_cost_for_mode(
    *,
    ctx: KeywordV3Context,
    to_mode: KeywordStrategyMode,
    prepared: PreparedList | None = None,
    eligibility: "KeywordV3Eligibility | None" = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> tuple[float, bool]:
    """Себестоимость режима через ``keyword_v3_ladder_view.cost_for_mode`` (SSOT)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
        cost_for_mode,
    )

    if ladder_inputs is None:
        if prepared is not None:
            ladder_inputs = ladder_inputs_for_prepared(prepared)
        else:
            ladder_inputs = LadderInputs.from_contexts([ctx])
    return cost_for_mode(
        ctx,
        to_mode,
        ladder_inputs=ladder_inputs,
        eligibility=eligibility,
    )


def resolve_effective_state_cost_for_mode(
    *,
    ctx: "KeywordV3Context",
    to_mode: KeywordStrategyMode,
    prepared: PreparedList | None = None,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    eligibility: "KeywordV3Eligibility | None" = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> tuple[float, bool]:
    """Единый API себестоимости target mode для ladder-фаз V3 (делегирует ``cost_for_mode``).

    Worst/per-mode cost — только из ``ladder_inputs`` (или пересборка из ``prepared``).

    Для ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV`` и ``MIN_CPA`` — ``pay_for_order``; O/C без CH → ``inf``.
    """
    elig = _eligibility_for_ctx(
        ctx, eligibility_by_ks_id, eligibility=eligibility
    )
    return _resolve_state_cost_for_mode(
        ctx=ctx,
        to_mode=to_mode,
        prepared=prepared,
        eligibility=elig,
        ladder_inputs=ladder_inputs,
    )


def _best_passing_in_mode_group(
    modes_group: tuple[KeywordStrategyMode, ...],
    *,
    ctx: "KeywordV3Context",
    state_candidates: dict[AggressionTargetMode, ModeCandidate],
    elig: "KeywordV3Eligibility | None",
    policy: SelectionPolicy,
    resolve: float,
    ladder_inputs: "LadderInputs | None",
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None,
) -> tuple[KeywordStrategyMode | None, float | None, bool]:
    """Max ``mode_level`` в группе с ``state_cost <= resolve`` и rec-gate."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        can_target_mode,
        clamp_target_mode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs as _LadderInputs,
    )

    ladder = (
        ladder_inputs
        if ladder_inputs is not None
        else _LadderInputs.from_contexts([ctx])
    )
    rec = ladder.rec_orders_per_view
    opc = ladder.orders_per_cart_for_ctx(ctx)
    group_best: KeywordStrategyMode | None = None
    group_cost: float | None = None
    group_imputed = False
    for to_mode in modes_group:
        capped = clamp_target_mode(elig, to_mode) if elig is not None else to_mode
        gate_status = state_rec_gate_status_for_mode(
            state_candidates,
            capped,
            policy,
            rec_orders_per_view=rec,
            orders_per_cart=opc,
        )
        if not rec_gate_allows_up(gate_status):
            continue
        if elig is not None and not can_target_mode(elig, capped):
            continue
        if mode_level(capped) > mode_level(policy.max_target_mode):
            continue
        cost, imputed = resolve_effective_state_cost_for_mode(
            ctx=ctx,
            to_mode=capped,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder,
        )
        if cost == float("inf") or cost > resolve:
            continue
        if group_best is None or mode_level(capped) > mode_level(group_best):
            group_best = capped
            group_cost = cost
            group_imputed = imputed
    return group_best, group_cost, group_imputed


def resolve_furthest_passing_up_mode(
    current: KeywordStrategyMode,
    *,
    ctx: "KeywordV3Context",
    catalog: dict[AggressionTargetMode, ModeCandidate],
    elig: "KeywordV3Eligibility | None",
    policy: SelectionPolicy,
    resolve: float,
    ladder_inputs: "LadderInputs | None",
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None,
) -> tuple[KeywordStrategyMode | None, float | None, bool]:
    """До упора passing UP: alias на текущем place + sequential новые place.

    Один итоговый ``to_mode`` на ключ (1 действие). Alias с тем же ``target_place``
    не считаются отдельными шагами.
    """
    furthest_mode: KeywordStrategyMode | None = None
    furthest_cost: float | None = None
    furthest_imputed = False

    def _take(
        mode: KeywordStrategyMode | None,
        cost: float | None,
        imputed: bool,
    ) -> None:
        nonlocal furthest_mode, furthest_cost, furthest_imputed
        if mode is None or cost is None or mode == current:
            return
        if mode_level(mode) <= mode_level(current):
            return
        if furthest_mode is None or mode_level(mode) > mode_level(furthest_mode):
            furthest_mode = mode
            furthest_cost = cost
            furthest_imputed = imputed

    if current != KeywordStrategyMode.OFF:
        current_c = candidate_for_strategy_mode(current, catalog)
        place = target_place_from_mode_candidate(current_c)
        if place is not None:
            same_place = logical_modes_at_target_place_above(current, place, catalog)
            sg, sc, si = _best_passing_in_mode_group(
                same_place,
                ctx=ctx,
                state_candidates=catalog,
                elig=elig,
                policy=policy,
                resolve=resolve,
                ladder_inputs=ladder_inputs,
                eligibility_by_ks_id=eligibility_by_ks_id,
            )
            _take(sg, sc, si)

    for group in iter_effective_upper_mode_groups(current, catalog):
        gb, gc, gi = _best_passing_in_mode_group(
            group,
            ctx=ctx,
            state_candidates=catalog,
            elig=elig,
            policy=policy,
            resolve=resolve,
            ladder_inputs=ladder_inputs,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if gb is None:
            break
        _take(gb, gc, gi)

    return furthest_mode, furthest_cost, furthest_imputed


def diagnose_passing_up_blockers(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
    sample_limit: int = 6,
) -> list[dict[str, object]]:
    """Dry-run: почему ключ не попал в passing pool (для debug-логов)."""
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    samples: list[dict[str, object]] = []
    for ctx, current in prepared:
        if len(samples) >= sample_limit:
            break
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        text = (ctx.keyword.text or "")[:40]
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            samples.append({"ks_id": ks_id, "text": text, "reason": "hard_status"})
            continue
        elig = _eligibility_for_ctx(ctx, eligibility_by_ks_id)
        if elig is not None and not elig.participates_in_ladder:
            samples.append({"ks_id": ks_id, "text": text, "reason": "no_ladder"})
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        capped, cost, _ = resolve_furthest_passing_up_mode(
            current,
            ctx=ctx,
            catalog=catalog,
            elig=elig,
            policy=policy,
            resolve=resolve,
            ladder_inputs=ladder,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if capped is None:
            samples.append(
                {
                    "ks_id": ks_id,
                    "text": text,
                    "from": current.name,
                    "reason": "no_passing_target",
                    "resolve": resolve,
                }
            )
            continue
        if capped == current:
            samples.append(
                {
                    "ks_id": ks_id,
                    "text": text,
                    "from": current.name,
                    "reason": "already_at_furthest",
                    "cost": cost,
                }
            )
            continue
        samples.append(
            {
                "ks_id": ks_id,
                "text": text,
                "from": current.name,
                "to": capped.name,
                "cost": cost,
                "reason": "would_pass",
            }
        )
    return samples


def _state_view_debug_row(view: _StateView) -> dict[str, object]:
    """Сериализация ``_StateView`` для NDJSON debug."""
    return {
        "ks_id": view.ks_id,
        "from": view.from_mode.name,
        "to": view.to_mode.name,
        "cost": view.cost,
        "imputed": view.imputed,
    }


def diagnose_cost_reallocation_snapshot(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
    head_limit: int = 8,
) -> dict[str, object]:
    """Dry-run COST_REALLOCATION (фаза R): potential vs active и причина простоя.

    Контракт rebalance в prod — ``plan_cost_reallocation`` (не ``plan_state_rebalance``).
    Порог: ``max(active state_cost) > min(potential passing cost)``; если potential пуст,
    fallback headroom — ``max(active) > resolve`` (нет UP-целей при ``state_cost ≤ resolve``).
    """
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    potential = collect_potential_passing_states(
        prepared,
        resolve=resolve,
        policy=policy,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder,
    )
    active_above_resolve = _collect_active_expensive(
        prepared,
        resolve=resolve,
        policy=policy,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder,
    )
    max_active_above_resolve = active_above_resolve[0] if active_above_resolve else None

    floor_source = "potential"
    if potential:
        min_potential = potential[0]
        min_cost = float(min_potential.cost)
    elif active_above_resolve:
        floor_source = "resolve_headroom"
        min_potential = None
        min_cost = float(resolve)
    else:
        floor_source = "none"
        min_potential = None
        min_cost = float("inf")

    active = _collect_active_more_expensive_than(
        prepared,
        min_cost=min_cost,
        policy=policy,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder,
    )
    max_active = active[0] if active else None

    stop_reason = "would_iterate"
    if floor_source == "none":
        stop_reason = "no_potential_passing"
    elif not active:
        stop_reason = "no_active_above_min_potential"
    elif max_active is not None:
        if float(max_active.cost) <= min_cost:
            stop_reason = "gap_closed"

    first_step: dict[str, object] | None = None
    if active and max_active is not None and stop_reason == "would_iterate":
        ctx_worst: KeywordV3Context | None = None
        for c, _m in prepared:
            ks = c.keyword.keyword_setting_original_id
            if ks is not None and int(ks) == max_active.ks_id:
                ctx_worst = c
                break
        if ctx_worst is not None:
            catalog = _mode_catalog_for_ctx(ctx_worst, prepared, ladder)
            step = resolve_next_effective_step_down(
                max_active.strategy_mode,
                catalog,
            )
            released = count_effective_released_aggression_steps(
                max_active.strategy_mode,
                step.next_mode,
                catalog,
            )
            first_step = {
                "ks_id": max_active.ks_id,
                "from": max_active.from_mode.name,
                "to": step.next_mode.name if step.next_mode else None,
                "released_steps": released,
                "hollow": released == 0,
            }
            if released == 0 and step.next_mode is not None:
                stop_reason = "hollow_effective_down"

    min_potential_row: dict[str, object] | None
    if min_potential is not None:
        min_potential_row = _state_view_debug_row(min_potential)
    elif floor_source == "resolve_headroom":
        min_potential_row = {
            "synthetic": True,
            "floor": floor_source,
            "cost": float(resolve),
        }
    else:
        min_potential_row = None

    result: dict[str, object] = {
        "resolve": float(resolve),
        "potential_count": len(potential),
        "floor_source": floor_source,
        "min_potential": min_potential_row,
        "active_above_min_count": len(active),
        "max_active": _state_view_debug_row(max_active) if max_active else None,
        "cost_gap": (
            float(max_active.cost) - min_cost
            if max_active is not None
            else None
        ),
        "stop_reason": stop_reason,
        "first_step_preview": first_step,
        "potential_head": [
            _state_view_debug_row(p) for p in potential[:head_limit]
        ],
        "active_head": [_state_view_debug_row(a) for a in active[:head_limit]],
        "active_above_resolve_count": len(active_above_resolve),
        "max_active_above_resolve": (
            _state_view_debug_row(max_active_above_resolve)
            if max_active_above_resolve is not None
            else None
        ),
    }
    if not potential:
        result["passing_blocker_samples"] = diagnose_passing_up_blockers(
            prepared,
            resolve=resolve,
            policy=policy,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder,
            sample_limit=head_limit,
        )
    return result


def _highest_passing_mode_in_upper_groups(
    modes_groups: tuple[tuple[KeywordStrategyMode, ...], ...],
    *,
    ctx: "KeywordV3Context",
    state_candidates: dict[AggressionTargetMode, ModeCandidate],
    elig: "KeywordV3Eligibility | None",
    policy: SelectionPolicy,
    resolve: float,
    ladder_inputs: "LadderInputs | None",
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None,
) -> tuple[KeywordStrategyMode | None, float | None, bool]:
    """Furthest passing mode: sequential effective groups, alias collapsed per group.

    Обходит ``modes_groups`` по порядку (OFF→…→MAX). В каждой группе — max
    ``mode_level`` с ``state_cost <= resolve``. Останавливается на первой группе без
    passing (нельзя перепрыгнуть через непроходимый ``target_place``).

    Args:
        state_candidates: уже вычисленный M/O/C catalog (``_mode_catalog_for_ctx`` у caller).
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        can_target_mode,
        clamp_target_mode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs as _LadderInputs,
    )

    ladder = (
        ladder_inputs
        if ladder_inputs is not None
        else _LadderInputs.from_contexts([ctx])
    )
    rec = ladder.rec_orders_per_view
    opc = ladder.orders_per_cart_for_ctx(ctx)
    furthest_mode: KeywordStrategyMode | None = None
    furthest_cost: float | None = None
    furthest_imputed = False
    for modes_group in modes_groups:
        group_best: KeywordStrategyMode | None = None
        group_cost: float | None = None
        group_imputed = False
        for to_mode in modes_group:
            capped = (
                clamp_target_mode(elig, to_mode) if elig is not None else to_mode
            )
            gate_status = state_rec_gate_status_for_mode(
                state_candidates,
                capped,
                policy,
                rec_orders_per_view=rec,
                orders_per_cart=opc,
            )
            if not rec_gate_allows_up(gate_status):
                continue
            if elig is not None and not can_target_mode(elig, capped):
                continue
            if mode_level(capped) > mode_level(policy.max_target_mode):
                continue
            cost, imputed = resolve_effective_state_cost_for_mode(
                ctx=ctx,
                to_mode=capped,
                eligibility_by_ks_id=eligibility_by_ks_id,
                ladder_inputs=ladder,
            )
            if cost == float("inf") or cost > resolve:
                continue
            if group_best is None or mode_level(capped) > mode_level(group_best):
                group_best = capped
                group_cost = cost
                group_imputed = imputed
        if group_best is None:
            break
        furthest_mode = group_best
        furthest_cost = group_cost
        furthest_imputed = group_imputed
    return furthest_mode, furthest_cost, furthest_imputed


def collect_potential_passing_states(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    overrides: dict[int, KeywordStrategyMode] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[_StateView]:
    """Кандидаты UP/realloc с ``state_cost <= resolve`` (passing potential)."""
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = (
            eligibility_by_ks_id.get(int(ks_id))
            if eligibility_by_ks_id
            else None
        )
        if elig is not None and not elig.participates_in_ladder:
            continue
        current = overrides.get(int(ks_id), stored_mode)
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        capped, cost, imputed = resolve_furthest_passing_up_mode(
            current,
            ctx=ctx,
            catalog=catalog,
            elig=elig,
            policy=policy,
            resolve=resolve,
            ladder_inputs=ladder,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if capped is None or cost is None or capped == current:
            continue
        current_c = candidate_for_strategy_mode(current, catalog)
        capped_c = candidate_for_strategy_mode(capped, catalog)
        if (
            current_c is not None
            and capped_c is not None
            and mode_candidates_same_effective_target(current_c, capped_c)
            and mode_level(capped) <= mode_level(current)
        ):
            continue
        out.append(
            _StateView(
                ks_id=int(ks_id),
                strategy_mode=capped,
                cost=cost,
                from_mode=current,
                to_mode=capped,
                imputed=imputed,
            )
        )
    out.sort(key=lambda x: x.cost)
    return out


def _append_cost_reallocation_final(
    actions: list[V3Action],
    *,
    ks_id: int,
    hard_status: int,
    stored_mode: KeywordStrategyMode,
    final_mode: KeywordStrategyMode,
) -> None:
    """Одно итоговое действие на ключ после итераций realloc (без пошаговых DOWN)."""
    if final_mode == stored_mode:
        return
    if final_mode == KeywordStrategyMode.OFF:
        actions.append(
            V3Action(
                action=V3ActionType.FORCE_OFF,
                keyword_setting_id=ks_id,
                reason="cost_reallocation_force_off",
            )
        )
        return
    if int(hard_status) == _HARD_STATUS_WHITE_LIST:
        actions.append(
            V3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=ks_id,
                target_strategy_mode=final_mode,
                reason="cost_reallocation_down",
            )
        )
        return
    actions.append(
        V3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=ks_id,
            reason="cost_reallocation_force_off",
        )
    )
    actions.append(
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ks_id,
            target_strategy_mode=final_mode,
            reason="cost_reallocation_down",
        )
    )


_ACTIVE_CLEANUP_MODES: tuple[KeywordStrategyMode, ...] = (
    KeywordStrategyMode.MIN_CPA,
    KeywordStrategyMode.OPTIMUM,
    KeywordStrategyMode.MAX_CONVERSION,
)

_REASON_ACTIVE_INVALID_DOWN = "active_invalid_state_down"
_REASON_ACTIVE_INVALID_FORCE_OFF = "active_invalid_state_force_off"


def _modes_below_for_cleanup(
    current: KeywordStrategyMode,
) -> tuple[KeywordStrategyMode, ...]:
    """Режимы ниже ``current`` (от ближайшего к MIN)."""
    cur_level = mode_level(current)
    below = [m for m in _ACTIVE_CLEANUP_MODES if mode_level(m) < cur_level]
    return tuple(reversed(below))


def _is_no_ch_profile_with_own_conv(
    eligibility: "KeywordV3Eligibility | None",
) -> bool:
    """Tier без CH-матрицы, operational MIN через ``keyword.pay_for_order``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
    )

    return (
        eligibility is not None
        and eligibility.data_tier
        == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV
    )


def _min_cpa_bound_by_pay_for_order(
    eligibility: "KeywordV3Eligibility | None",
) -> bool:
    """MIN-only + ``target_place=0``: NO CH или collapsed CH ladder + pay_for_order."""
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode

    return (
        eligibility is not None
        and eligibility.participates_in_ladder
        and eligibility.target_place_fallback_zero
        and eligibility.allowed_modes == frozenset({KeywordStrategyMode.MIN_CPA})
    )


def _cleanup_diag(
    *,
    cur_c: ModeCandidate | None,
    position: int | None,
    cost: float,
    source_value: str,
    invalid_flags: list[str],
) -> dict[str, object]:
    """Общий snapshot для логов active_invalid_cleanup."""
    return {
        "current_candidate_valid": (
            None if cur_c is None else bool(cur_c.is_valid)
        ),
        "current_candidate_position": position,
        "current_state_cost": None if cost == float("inf") else float(cost),
        "current_state_cost_source": source_value,
        "invalid_flags": tuple(invalid_flags),
    }


def _active_state_invalid_no_ch_for_cleanup(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    max_pay_for_order: float,
    ladder_inputs: "LadderInputs",
    eligibility: "KeywordV3Eligibility",
) -> tuple[bool, dict[str, object]]:
    """Cleanup для NO CH + own conv: CH-кандидат не обязателен, operational cost — SSOT."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        aggression_target_for_stored_mode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderCostSource,
        cost_for_mode,
        resolve_ladder_stage_display,
    )

    agg = aggression_target_for_stored_mode(current)
    if agg is None:
        return False, {}
    stage = resolve_ladder_stage_display(
        ctx, ladder_inputs, eligibility=eligibility
    ).stages[agg]
    cost, _imputed = cost_for_mode(
        ctx,
        current,
        ladder_inputs=ladder_inputs,
        eligibility=eligibility,
    )
    invalid_flags: list[str] = []

    if current == KeywordStrategyMode.MIN_CPA:
        if stage.source == LadderCostSource.PAY_FOR_ORDER and cost != float("inf"):
            if not keyword_pay_for_order_exceeds_max(
                ctx, max_pay_for_order=max_pay_for_order
            ):
                return False, _cleanup_diag(
                    cur_c=None,
                    position=None,
                    cost=cost,
                    source_value=stage.source.value,
                    invalid_flags=(),
                )
        if keyword_pay_for_order_exceeds_max(
            ctx, max_pay_for_order=max_pay_for_order
        ):
            invalid_flags.append("pay_for_order_above_max")
        if cost == float("inf"):
            invalid_flags.append("cost_inf")
        if stage.source == LadderCostSource.WORST:
            invalid_flags.append("cost_source_worst")
        if stage.source == LadderCostSource.NONE:
            invalid_flags.append("no_operational_pay_for_order")
        return bool(invalid_flags), _cleanup_diag(
            cur_c=None,
            position=None,
            cost=cost,
            source_value=stage.source.value,
            invalid_flags=invalid_flags,
        )

    if cost == float("inf"):
        invalid_flags.append("cost_inf")
    if stage.source == LadderCostSource.WORST:
        invalid_flags.append("cost_source_worst")
    if stage.source == LadderCostSource.NONE or not stage.is_valid:
        invalid_flags.append("no_ch_oc_operational_cost")
    return bool(invalid_flags), _cleanup_diag(
        cur_c=None,
        position=None,
        cost=cost,
        source_value=stage.source.value,
        invalid_flags=invalid_flags,
    )


def _active_state_invalid_for_cleanup(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    catalog: dict[AggressionTargetMode, ModeCandidate],
    ladder_inputs: "LadderInputs",
    eligibility: "KeywordV3Eligibility | None",
    max_pay_for_order: float,
) -> tuple[bool, dict[str, object]]:
    """Нужен ли cleanup: stored active mode не согласован с operational cost / CH-матрицей."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        aggression_target_for_stored_mode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
        target_place_from_mode_candidate,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        min_cpa_operational_via_pay_for_order,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderCostSource,
        cost_for_mode,
        resolve_ladder_stage_display,
    )

    if min_cpa_operational_via_pay_for_order(ctx, eligibility, catalog):
        assert eligibility is not None
        return _active_state_invalid_no_ch_for_cleanup(
            ctx,
            current,
            max_pay_for_order=max_pay_for_order,
            ladder_inputs=ladder_inputs,
            eligibility=eligibility,
        )

    agg = aggression_target_for_stored_mode(current)
    if agg is None:
        return False, {}
    cur_c = candidate_for_strategy_mode(current, catalog)
    stage = resolve_ladder_stage_display(
        ctx, ladder_inputs, eligibility=eligibility
    ).stages[agg]
    cost, _imputed = cost_for_mode(
        ctx,
        current,
        ladder_inputs=ladder_inputs,
        eligibility=eligibility,
    )
    position = target_place_from_mode_candidate(cur_c)
    invalid_flags: list[str] = []
    if cur_c is None:
        invalid_flags.append("missing_candidate")
    else:
        if not cur_c.is_valid:
            invalid_flags.append("candidate_not_valid")
        if cur_c.position is None:
            invalid_flags.append("candidate_position_none")
    if cost == float("inf"):
        invalid_flags.append("cost_inf")
    if stage.source == LadderCostSource.WORST:
        invalid_flags.append("cost_source_worst")
    if position is None:
        invalid_flags.append("target_place_none")
    return bool(invalid_flags), _cleanup_diag(
        cur_c=cur_c,
        position=position,
        cost=cost,
        source_value=stage.source.value,
        invalid_flags=invalid_flags,
    )


def _lower_modes_valid_for_cleanup(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    catalog: dict[AggressionTargetMode, ModeCandidate],
    ladder_inputs: "LadderInputs",
    eligibility: "KeywordV3Eligibility | None",
    max_pay_for_order: float,
    resolve: float | None,
) -> list[tuple[KeywordStrategyMode, float]]:
    """Режимы ниже ``current``, проходящие validity + max (+ resolve при заданном resolve)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
        target_place_from_mode_candidate,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        can_target_mode,
        min_cpa_operational_via_pay_for_order,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderCostSource,
        cost_for_mode,
        resolve_ladder_stage_display,
    )

    resolve_limit: float | None = None
    if resolve is not None and float(resolve) > 0:
        resolve_limit = float(resolve)
    passing: list[tuple[KeywordStrategyMode, float]] = []
    for mode in _modes_below_for_cleanup(current):
        if eligibility is not None and not can_target_mode(eligibility, mode):
            continue
        if min_cpa_operational_via_pay_for_order(ctx, eligibility, catalog):
            if mode != KeywordStrategyMode.MIN_CPA:
                continue
            stage = resolve_ladder_stage_display(
                ctx, ladder_inputs, eligibility=eligibility
            ).stages[AggressionTargetMode.MIN_CPA]
            if stage.source == LadderCostSource.WORST:
                continue
            cost, _ = cost_for_mode(
                ctx,
                mode,
                ladder_inputs=ladder_inputs,
                eligibility=eligibility,
            )
            if cost == float("inf") or float(cost) > float(max_pay_for_order):
                continue
            if resolve_limit is not None and float(cost) > resolve_limit:
                continue
            if stage.source != LadderCostSource.PAY_FOR_ORDER:
                continue
            passing.append((mode, float(cost)))
            continue
        mc = candidate_for_strategy_mode(mode, catalog)
        if mc is None or not mc.is_valid or mc.position is None:
            continue
        if target_place_from_mode_candidate(mc) is None:
            continue
        stage = resolve_ladder_stage_display(
            ctx, ladder_inputs, eligibility=eligibility
        ).stages[AggressionTargetMode[mode.name]]
        if stage.source == LadderCostSource.WORST:
            continue
        cost, _ = cost_for_mode(
            ctx,
            mode,
            ladder_inputs=ladder_inputs,
            eligibility=eligibility,
        )
        if cost == float("inf") or float(cost) > float(max_pay_for_order):
            continue
        if resolve_limit is not None and float(cost) > resolve_limit:
            continue
        passing.append((mode, float(cost)))
    return passing


def _pick_lower_cleanup_mode(
    passing: list[tuple[KeywordStrategyMode, float]],
) -> KeywordStrategyMode | None:
    """Самый высокий (ближайший к current) lower mode из passing."""
    if not passing:
        return None
    return max(passing, key=lambda t: mode_level(t[0]))[0]


def _append_active_invalid_cleanup(
    actions: list[V3Action],
    *,
    ks_id: int,
    current: KeywordStrategyMode,
    target: KeywordStrategyMode,
    hard_status: int,
    reason: str,
) -> None:
    """WL: DOWN; авто: FORCE_OFF (+ UP до цели, если не OFF)."""
    if target == KeywordStrategyMode.OFF:
        actions.append(
            V3Action(
                action=V3ActionType.FORCE_OFF,
                keyword_setting_id=ks_id,
                reason=reason,
            )
        )
        return
    if int(hard_status) == _HARD_STATUS_WHITE_LIST:
        actions.append(
            V3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=ks_id,
                target_strategy_mode=target,
                reason=reason,
            )
        )
        return
    actions.append(
        V3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=ks_id,
            reason=reason,
        )
    )
    actions.append(
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ks_id,
            target_strategy_mode=target,
            reason=reason,
        )
    )


def plan_active_invalid_state_cleanup(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    resolve: float | None = None,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """Сброс active MIN/OPT/MAX при невалидной ступени или worst-only cost текущего режима.

    Вызывается на каждом NORMAL-тике после ``plan_data_bootstrap_v3``, до realloc/expansion.
    Не трогает rec-gate и ``target_place_sync``.
    """
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    actions: list[V3Action] = []
    max_pfo = float(max_pay_for_order)

    for ctx, current in prepared:
        if current not in _ACTIVE_CLEANUP_MODES:
            continue
        hard_status = int(ctx.keyword.hard_status)
        if hard_status not in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = _eligibility_for_ctx(ctx, eligibility_by_ks_id)
        if elig is not None and not elig.participates_in_ladder:
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        is_invalid, diag = _active_state_invalid_for_cleanup(
            ctx,
            current,
            catalog=catalog,
            ladder_inputs=ladder,
            eligibility=elig,
            max_pay_for_order=max_pfo,
        )
        if not is_invalid:
            continue
        passing = _lower_modes_valid_for_cleanup(
            ctx,
            current,
            catalog=catalog,
            ladder_inputs=ladder,
            eligibility=elig,
            max_pay_for_order=max_pfo,
            resolve=resolve,
        )
        lower_names = [m.name for m, _ in passing]
        target = _pick_lower_cleanup_mode(passing)
        if target is not None:
            _append_active_invalid_cleanup(
                actions,
                ks_id=int(ks_id),
                current=current,
                target=target,
                hard_status=hard_status,
                reason=_REASON_ACTIVE_INVALID_DOWN,
            )
            action_kind = f"DOWN->{target.name}"
        else:
            _append_active_invalid_cleanup(
                actions,
                ks_id=int(ks_id),
                current=current,
                target=KeywordStrategyMode.OFF,
                hard_status=hard_status,
                reason=_REASON_ACTIVE_INVALID_FORCE_OFF,
            )
            action_kind = "FORCE_OFF"
        logger.info(
            "v3 active_invalid_cleanup kw=%s ks_id=%s current=%s "
            "candidate_valid=%s position=%s cost=%s source=%s "
            "lower_valid_modes=%s action=%s flags=%s",
            ctx.keyword.text,
            ks_id,
            current.name,
            diag.get("current_candidate_valid"),
            diag.get("current_candidate_position"),
            diag.get("current_state_cost"),
            diag.get("current_state_cost_source"),
            lower_names,
            action_kind,
            diag.get("invalid_flags"),
        )
    return actions


def plan_cost_reallocation(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """COST_REALLOCATION: - перераспределение стейтов, чтобы агрессивность осталась та же,
    но стейты перераспределились от дорогих к дешевым.
    """
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    stored_by_ks: dict[int, tuple[KeywordStrategyMode, int]] = {}
    for ctx, mode in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is not None:
            stored_by_ks[int(ks_id)] = (mode, int(ctx.keyword.hard_status))

    overrides: dict[int, KeywordStrategyMode] = {}
    released_steps = 0
    last_down_sig: tuple[int, str, str] | None = None
    for _ in range(50):
        potential_passing = collect_potential_passing_states(
            prepared,
            resolve=resolve,
            policy=policy,
            eligibility_by_ks_id=eligibility_by_ks_id,
            overrides=overrides,
            ladder_inputs=ladder,
        )
        if potential_passing:
            min_potential_cost = potential_passing[0].cost
        else:
            min_potential_cost = float(resolve)
        active_expensive = _collect_active_more_expensive_than(
            prepared,
            min_cost=min_potential_cost,
            policy=policy,
            eligibility_by_ks_id=eligibility_by_ks_id,
            overrides=overrides,
            ladder_inputs=ladder,
        )
        if not active_expensive:
            break
        worst_active = active_expensive[0]
        if eligibility_by_ks_id is not None:
            elig = eligibility_by_ks_id.get(worst_active.ks_id)
            if elig is not None and not elig.participates_in_ladder:
                break
        if worst_active.cost <= min_potential_cost:
            break
        ctx_worst: KeywordV3Context | None = None
        for c, _m in prepared:
            ks = c.keyword.keyword_setting_original_id
            if ks is not None and int(ks) == worst_active.ks_id:
                ctx_worst = c
                break
        if ctx_worst is None:
            break
        catalog = _mode_catalog_for_ctx(ctx_worst, prepared, ladder)
        step = StepManager.resolve_down(worst_active.strategy_mode, catalog)
        log_skipped_aliases(ctx_worst.keyword.text, step.skipped_aliases)
        if step.to_mode is None:
            break
        if step.released_aggression_steps == 0:
            logger.debug(
                "v3 realloc hollow down kw=%s: %s -> %s same target_place, stop",
                ctx_worst.keyword.text,
                worst_active.strategy_mode.name,
                step.to_mode.name,
            )
            break
        step_sig = (
            worst_active.ks_id,
            worst_active.strategy_mode.name,
            step.to_mode.name,
        )
        if last_down_sig == step_sig:
            break
        released_steps += step.released_aggression_steps
        overrides[worst_active.ks_id] = step.to_mode
        last_down_sig = step_sig

    if released_steps:
        logger.debug("v3 cost_reallocation released_steps=%s", released_steps)

    down_actions: list[V3Action] = []
    for ks_id, final_mode in overrides.items():
        stored = stored_by_ks.get(ks_id)
        if stored is None:
            continue
        stored_mode, hard_status = stored
        ctx_stored: KeywordV3Context | None = None
        for c, _m in prepared:
            sid = c.keyword.keyword_setting_original_id
            if sid is not None and int(sid) == ks_id:
                ctx_stored = c
                break
        if ctx_stored is not None:
            catalog = _mode_catalog_for_ctx(ctx_stored, prepared, ladder)
            stored_c = candidate_for_strategy_mode(stored_mode, catalog)
            final_c = candidate_for_strategy_mode(final_mode, catalog)
            if mode_candidates_same_effective_target(stored_c, final_c):
                logger.debug(
                    "v3 skip realloc kw=%s: stored %s and final %s same target_place",
                    ctx_stored.keyword.text,
                    stored_mode.name,
                    final_mode.name,
                )
                continue
        _append_cost_reallocation_final(
            down_actions,
            ks_id=ks_id,
            hard_status=hard_status,
            stored_mode=stored_mode,
            final_mode=final_mode,
        )
    return down_actions


def plan_profitable_expansion(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """PROFITABLE_EXPANSION (M1): UP до max passing mode с учётом eligibility."""
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    actions: list[V3Action] = []
    for ctx, current_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = (
            eligibility_by_ks_id.get(int(ks_id))
            if eligibility_by_ks_id
            else None
        )
        if elig is not None and not elig.participates_in_ladder:
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        best_mode, best_cost, best_imputed = resolve_furthest_passing_up_mode(
            current_mode,
            ctx=ctx,
            catalog=catalog,
            elig=elig,
            policy=policy,
            resolve=resolve,
            ladder_inputs=ladder,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if best_mode is None or best_mode == current_mode:
            continue
        if mode_level(best_mode) <= mode_level(current_mode):
            continue
        actions.append(
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=ks_id,
                target_strategy_mode=best_mode,
                reason="profitable_expansion",
                selection_log=V3SelectionLog(
                    mechanism="profitable_expansion",
                    state_cost=best_cost,
                    pay_for_order=float(ctx.keyword.pay_for_order or 0.0),
                    from_mode=current_mode.name,
                    to_mode=best_mode.name,
                    move_kind=f"{current_mode.name.lower()}_to_{best_mode.name.lower()}",
                    imputed=best_imputed,
                ),
            )
        )
    return actions


def diagnose_max_cpa_guard_keyword(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    max_pay_for_order: float,
    prepared: PreparedList,
    shelf_click_mode: "ShelfClickMode",
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    guard_would_run: bool | None = None,
    fact_pay_for_order: float | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> dict[str, object]:
    """Диагностика MAX_CPA_GUARD для одного ключа (dry-run / support).

    Для паритета с orchestrator передайте тот же ``LadderInputs``, что в
    ``plan_max_cpa_guard`` (``rk_orders_per_cart``, ``rec_orders_per_view``).
    Без ``ladder_inputs`` строится из ``prepared`` без RK/rec — CPO может расходиться
    с production guard.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        operational_cpo_at_keyword_target_place,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    if ladder_inputs is None:
        ladder = ladder_inputs_for_prepared(prepared)
        ladder_inputs_source = "derived_from_prepared"
    else:
        ladder = ladder_inputs
        ladder_inputs_source = "ladder_inputs"
    ks_id = ctx.keyword.keyword_setting_original_id
    hard_status = int(ctx.keyword.hard_status)

    catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
    operational_cpo = operational_cpo_at_keyword_target_place(
        ctx, ladder_inputs=ladder
    )
    mode_costs: dict[str, float | None] = {}
    for mode in (
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        cost, _ = resolve_effective_state_cost_for_mode(
            ctx=ctx,
            to_mode=mode,
            prepared=prepared,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder,
        )
        mode_costs[mode.name] = None if cost == float("inf") else float(cost)

    cur_cost, _ = resolve_effective_state_cost_for_mode(
        ctx=ctx,
        to_mode=current,
        prepared=prepared,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder,
    )
    current_state_cost = None if cur_cost == float("inf") else float(cur_cost)

    skip_reasons: list[str] = []
    trim_target: KeywordStrategyMode | None = None

    if guard_would_run is False:
        skip_reasons.append("guard_not_run")
    if current == KeywordStrategyMode.OFF:
        skip_reasons.append("current_off")
    elif hard_status not in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST):
        skip_reasons.append(f"hard_status={hard_status}_not_managed")
    else:
        elig = _eligibility_for_ctx(ctx, eligibility_by_ks_id)
        if _min_cpa_bound_by_pay_for_order(elig):
            if keyword_pay_for_order_exceeds_max(
                ctx, max_pay_for_order=float(max_pay_for_order)
            ):
                trim_target = KeywordStrategyMode.OFF
            else:
                skip_reasons.append("no_ch_pfo_under_max")
        else:
            trim_target = _find_trim_target_mode(
                ctx,
                current,
                catalog=catalog,
                cost_ceiling=float(max_pay_for_order),
                ladder_inputs=ladder,
                policy=policy,
                eligibility_by_ks_id=eligibility_by_ks_id,
            )
            if trim_target == current:
                if (
                    current_state_cost is not None
                    and current_state_cost <= max_pay_for_order
                ):
                    skip_reasons.append("current_state_cost_under_max")
                else:
                    skip_reasons.append("trim_target_equals_current")
            else:
                if should_skip_trim_for_same_effective_target(
                    ctx=ctx,
                    current=current,
                    trim_target=trim_target,
                    catalog=catalog,
                    cost_ceiling=float(max_pay_for_order),
                    ladder_inputs=ladder,
                ):
                    skip_reasons.append("same_target_place")
                elif (
                    trim_target == KeywordStrategyMode.OFF
                    and mode_costs.get("MIN_CPA") is not None
                    and float(mode_costs["MIN_CPA"] or 0) > max_pay_for_order
                ):
                    skip_reasons.append("min_state_cost_above_max")

    guard_action: V3Action | None = None
    if ks_id is not None and trim_target is not None and trim_target != current:
        acts = plan_max_cpa_guard(
            [(ctx, current)],
            max_pay_for_order=float(max_pay_for_order),
            shelf_click_mode=shelf_click_mode,
            aggressiveness=aggressiveness,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder,
        )
        for act in acts:
            if act.keyword_setting_id == int(ks_id):
                guard_action = act
                break
        if guard_action is None and not skip_reasons:
            skip_reasons.append("plan_max_cpa_guard_no_action")

    return {
        "guard_would_run": guard_would_run,
        "guard_condition_fact_gt_max": (
            fact_pay_for_order is not None
            and float(fact_pay_for_order) > float(max_pay_for_order)
        ),
        "fact_pay_for_order": fact_pay_for_order,
        "plan_max_pay_for_order": float(max_pay_for_order),
        "current_mode": current.name,
        "stored_strategy_mode": current.name,
        "hard_status": hard_status,
        "current_state_cost": current_state_cost,
        "M_state_cost": mode_costs.get("MIN_CPA"),
        "O_state_cost": mode_costs.get("OPTIMUM"),
        "C_state_cost": mode_costs.get("MAX_CONVERSION"),
        "trim_target_mode": trim_target.name if trim_target is not None else None,
        "guard_action": (
            {
                "action": guard_action.action.value,
                "target_strategy_mode": (
                    guard_action.target_strategy_mode.name
                    if guard_action.target_strategy_mode is not None
                    else None
                ),
                "reason": guard_action.reason,
            }
            if guard_action is not None
            else None
        ),
        "guard_skip_reason": ";".join(skip_reasons) if skip_reasons else None,
        "ladder_inputs_source": ladder_inputs_source,
        "campaign_orders_per_cart_7d": ladder.campaign_orders_per_cart_7d,
        "rk_orders_per_cart": ladder.campaign_orders_per_cart_7d,
        "rec_orders_per_view": ladder.rec_orders_per_view,
        "operational_cpo_at_target_place": (
            None if operational_cpo is None else float(operational_cpo)
        ),
    }


def plan_max_cpa_guard(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """MAX_CPA_GUARD: trim только по ``plan.max_pay_for_order``."""
    actions = plan_campaign_trim_by_max_state_cost(
        prepared,
        max_pay_for_order=float(max_pay_for_order),
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
    )
    return [
        act.model_copy(
            update={"reason": act.reason.replace("trim_", "max_cpa_guard_")}
        )
        for act in actions
    ]


def plan_mass_cheap_promotion(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """M1: для каждого ключа поднять до highest passing state из класса A."""
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    actions: list[V3Action] = []
    for ctx, current_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        best_mode, best_cost, best_imputed = resolve_furthest_passing_up_mode(
            current_mode,
            ctx=ctx,
            catalog=catalog,
            elig=None,
            policy=policy,
            resolve=resolve,
            ladder_inputs=ladder,
            eligibility_by_ks_id=None,
        )
        if best_mode is None or best_mode == current_mode:
            continue
        if mode_level(best_mode) <= mode_level(current_mode):
            continue
        actions.append(
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=ks_id,
                target_strategy_mode=best_mode,
                reason="m1_mass_cheap_promotion",
                selection_log=V3SelectionLog(
                    mechanism="m1",
                    state_cost=best_cost,
                    pay_for_order=float(ctx.keyword.pay_for_order or 0.0),
                    from_mode=current_mode.name,
                    to_mode=best_mode.name,
                    move_kind=f"{current_mode.name.lower()}_to_{best_mode.name.lower()}",
                    imputed=best_imputed,
                ),
            )
        )
    return actions


def _collect_active_more_expensive_than(
    prepared: PreparedList,
    *,
    min_cost: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    overrides: dict[int, KeywordStrategyMode] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[_StateView]:
    """Активные ключи, у которых ``state_cost(current) > min_cost``."""
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        current = overrides.get(int(ks_id), stored_mode)
        if current == KeywordStrategyMode.OFF:
            continue
        if mode_level(current) > mode_level(policy.max_target_mode):
            continue
        cost, imputed = resolve_effective_state_cost_for_mode(
            ctx=ctx,
            to_mode=current,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder,
        )
        if cost == float("inf") or cost <= min_cost:
            continue
        out.append(
            _StateView(
                ks_id=int(ks_id),
                strategy_mode=current,
                cost=cost,
                from_mode=current,
                to_mode=current,
                imputed=imputed,
            )
        )
    out.sort(key=lambda x: x.cost, reverse=True)
    return out


def _collect_active_expensive(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
    overrides: dict[int, KeywordStrategyMode] | None = None,
) -> list[_StateView]:
    """Активные ключи с ``state_cost(current) > resolve`` (тот же cost SSOT, что realloc DOWN)."""
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        current = overrides.get(int(ks_id), stored_mode)
        if current == KeywordStrategyMode.OFF:
            continue
        if mode_level(current) > mode_level(policy.max_target_mode):
            continue
        cost, imputed = resolve_effective_state_cost_for_mode(
            ctx=ctx,
            to_mode=current,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder,
        )
        if cost == float("inf") or cost <= resolve:
            continue
        out.append(
            _StateView(
                ks_id=int(ks_id),
                strategy_mode=current,
                cost=cost,
                from_mode=current,
                to_mode=current,
                imputed=imputed,
            )
        )
    out.sort(key=lambda x: x.cost, reverse=True)
    return out


def _collect_potential_expensive(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    ladder_inputs: "LadderInputs | None" = None,
    overrides: dict[int, KeywordStrategyMode] | None = None,
) -> list[_StateView]:
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        current = overrides.get(ks_id, stored_mode)
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        step = resolve_next_effective_step_up(current, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        if step.next_mode is None:
            continue
        to_mode = step.next_mode
        if mode_level(to_mode) > mode_level(policy.max_target_mode):
            continue
        gate_status = state_rec_gate_status_for_mode(
            catalog,
            to_mode,
            policy,
            rec_orders_per_view=ladder.rec_orders_per_view,
            orders_per_cart=ladder.orders_per_cart_for_ctx(ctx),
        )
        if not rec_gate_allows_up(gate_status):
            continue
        cost, imputed = _resolve_state_cost_for_mode(
            ctx=ctx,
            to_mode=to_mode,
            ladder_inputs=ladder,
        )
        if cost == float("inf") or cost <= resolve:
            continue
        out.append(
            _StateView(
                ks_id=ks_id,
                strategy_mode=to_mode,
                cost=cost,
                from_mode=current,
                to_mode=to_mode,
                imputed=imputed,
            )
        )
    out.sort(key=lambda x: x.cost)
    return out


def plan_state_rebalance(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """M2: итеративно убрать разрыв max(active_B) > min(potential_B).

    ``released_steps`` (локально ``budget``) — только effective DOWN (place или OFF).
    """
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    overrides: dict[int, KeywordStrategyMode] = {}
    down_actions: list[V3Action] = []
    up_actions: list[V3Action] = []
    released_steps = 0
    for _ in range(50):
        active_expensive = _collect_active_expensive(
            prepared,
            resolve=resolve,
            policy=policy,
            ladder_inputs=ladder,
            overrides=overrides,
        )
        potential_expensive = _collect_potential_expensive(
            prepared,
            resolve=resolve,
            policy=policy,
            ladder_inputs=ladder,
            overrides=overrides,
        )
        if not active_expensive or not potential_expensive:
            break
        worst_active = active_expensive[0]
        cheapest_potential = potential_expensive[0]
        if worst_active.cost <= cheapest_potential.cost:
            break
        ctx_worst: "KeywordV3Context | None" = None
        for c, _m in prepared:
            ks = c.keyword.keyword_setting_original_id
            if ks is not None and int(ks) == worst_active.ks_id:
                ctx_worst = c
                break
        if ctx_worst is None:
            break
        catalog = _mode_catalog_for_ctx(ctx_worst, prepared, ladder)
        step = resolve_next_effective_step_down(
            worst_active.strategy_mode,
            catalog,
        )
        log_skipped_aliases(ctx_worst.keyword.text, step.skipped_aliases)
        nxt = step.next_mode
        if nxt is None:
            break
        released = count_effective_released_aggression_steps(
            worst_active.strategy_mode,
            nxt,
            catalog,
        )
        if released == 0:
            logger.debug(
                "v3 m2_rebalance hollow down kw=%s: %s -> %s",
                ctx_worst.keyword.text,
                worst_active.strategy_mode.name,
                nxt.name,
            )
            break
        overrides[worst_active.ks_id] = nxt
        released_steps += released
        if nxt == KeywordStrategyMode.OFF:
            down_actions.append(
                V3Action(
                    action=V3ActionType.FORCE_OFF,
                    keyword_setting_id=worst_active.ks_id,
                    reason="m2_rebalance_force_off",
                )
            )
        else:
            down_actions.append(
                V3Action(
                    action=V3ActionType.DOWN,
                    keyword_setting_id=worst_active.ks_id,
                    target_strategy_mode=nxt,
                    reason="m2_rebalance_down",
                )
            )
    for _ in range(released_steps):
        potential_expensive = _collect_potential_expensive(
            prepared,
            resolve=resolve,
            policy=policy,
            ladder_inputs=ladder,
            overrides=overrides,
        )
        if not potential_expensive:
            break
        target = potential_expensive[0]
        overrides[target.ks_id] = target.to_mode
        up_actions.append(
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=target.ks_id,
                target_strategy_mode=target.to_mode,
                reason="m2_rebalance_up",
            )
        )
    return down_actions + up_actions


def plan_headroom_plus_one(
    prepared: PreparedList,
    *,
    resolve: float,
    fact_pay_for_order: float | None,
    policy: SelectionPolicy,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """M3: один UP на cheapest effective transition если есть headroom.

    Кандидаты уже отфильтрованы ``collect_transition_candidates`` / effective steps;
    не требуем ``mode_level(to) == mode_level(from) + 1`` (alias O=M → MIN→MAX).
    """
    if fact_pay_for_order is None or fact_pay_for_order >= 0.9 * resolve:
        return []
    candidates = collect_transition_candidates(
        prepared, policy=policy, ladder_inputs=ladder_inputs
    )
    if not candidates:
        return []
    best = min(candidates, key=lambda c: c.state_cost)
    return [
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=best.keyword_setting_id,
            target_strategy_mode=best.to_mode,
            reason="m3_headroom_plus_one",
            selection_log=V3SelectionLog(
                mechanism="m3",
                state_cost=best.state_cost,
                pay_for_order=best.pay_for_order,
                from_mode=best.from_mode.name,
                to_mode=best.to_mode.name,
                move_kind=best.move_kind.value,
                imputed=best.imputed,
            ),
        )
    ]


def merge_and_dedup_actions(
    cleanup_actions: list[V3Action],
    m1_actions: list[V3Action],
    m2_actions: list[V3Action],
    m3_actions: list[V3Action],
) -> list[V3Action]:
    """Слить действия с приоритетом cleanup > M2 > M1 > M3 по ``keyword_setting_id``.

    Внутри одного входного списка все действия для одного ключа сохраняются
    (например N-state: FORCE_OFF → UP). Между списками для ключа побеждает bucket
    более высокого приоритета целиком — все его действия по этому ключу.
    """
    buckets: list[list[V3Action]] = [
        m3_actions,
        m1_actions,
        m2_actions,
        cleanup_actions,
    ]
    winner_bucket: dict[int, int] = {}
    for bidx, bucket in enumerate(buckets):
        for action in bucket:
            if action.action == V3ActionType.DO_NOTHING:
                continue
            ks_id = action.keyword_setting_id
            if ks_id is None:
                continue
            winner_bucket[int(ks_id)] = bidx

    result: list[V3Action] = []
    for bidx, bucket in enumerate(buckets):
        for action in bucket:
            if action.action == V3ActionType.DO_NOTHING:
                continue
            ks_id = action.keyword_setting_id
            if ks_id is None:
                result.append(action)
                continue
            if winner_bucket.get(int(ks_id)) == bidx:
                result.append(action)
    return result
