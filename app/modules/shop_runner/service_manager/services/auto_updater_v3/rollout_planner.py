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
    count_effective_released_aggression_steps,
    iter_effective_upper_modes,
    log_skipped_aliases,
    mode_candidates_same_effective_target,
    resolve_next_effective_step_down,
    resolve_next_effective_step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    effective_conv_for_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
    collect_transition_candidates,
    missing_target_matrix_from_catalog,
    passes_rec_gate_for_up,
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
    """M/O/C кандидаты для effective ladder steps."""
    conv = _conv_for_ctx(ctx, prepared)
    rk = ladder_inputs.rk_orders_per_cart if ladder_inputs is not None else None
    return build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
        conv_views_to_orders=conv if rk is None else None,
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
    rk = ladder_inputs.rk_orders_per_cart if ladder_inputs is not None else None
    if mode == KeywordStrategyMode.OFF:
        cand = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
            conv_views_to_orders=conv if rk is None else None,
            rk_orders_per_cart=rk,
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


def keyword_pay_for_order_exceeds_max(
    ctx: "KeywordV3Context",
    *,
    max_pay_for_order: float,
) -> bool:
    """True, если ``keyword.pay_for_order`` (как в UI) строго выше ``plan.max_pay_for_order``.

    Для tier ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV`` — основной критерий FORCE_OFF при
    OVERSPEND/trim (нет CH ``state_cost``; imputed conv не используется).
    """
    pfo = ctx.keyword.pay_for_order
    if pfo is None:
        return False
    return float(pfo) > float(max_pay_for_order)


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
) -> list[V3Action]:
    """OVERSPEND: массовый OFF по ключам выше max, иначе один DOWN."""
    forced = plan_overspend_force_off_over_max(
        prepared, max_pay_for_order=max_pay_for_order
    )
    if forced:
        return forced
    return plan_rollout_down_one(prepared, reason="overspend")


def _find_trim_target_mode(
    ctx: "KeywordV3Context",
    current: KeywordStrategyMode,
    *,
    catalog: dict[AggressionTargetMode, ModeCandidate],
    max_pay_for_order: float,
    ladder_inputs: "LadderInputs",
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> KeywordStrategyMode:
    """Ближайший режим ≤ current, где ``state_cost <= max_pay_for_order``; иначе OFF."""
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
        cost, _ = resolve_effective_state_cost_for_mode(
            ctx=ctx,
            to_mode=mode,
            ladder_inputs=ladder_inputs,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if cost != float("inf") and cost <= max_pay_for_order:
            return mode
        step = resolve_next_effective_step_down(mode, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        if step.next_mode is None:
            return KeywordStrategyMode.OFF
        mode = step.next_mode


def _append_trim_to_mode(
    actions: list[V3Action],
    *,
    ks_id: int,
    current: KeywordStrategyMode,
    target: KeywordStrategyMode,
    hard_status: int,
) -> None:
    """WL: DOWN; авто: FORCE_OFF (+ UP до целевого режима, если не OFF)."""
    reason = "trim_max_state_cost"
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


def plan_campaign_trim_by_max_state_cost(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    shelf_click_mode: "ShelfClickMode",
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> list[V3Action]:
    """Снизить режим до ближайшего с ``state_cost <= plan.max_pay_for_order`` (не resolve).

    Вызывается из orchestrator, когда ``fact.pay_for_order > plan.max_pay_for_order``.

    Для ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV`` (нет CH-матрицы): не пропускаем tier —
    сравниваем ``keyword.pay_for_order`` с max и при превышении → OFF. Imputed conv
    и ``resolve_keyword_v2_pay_for_order_cost`` здесь не участвуют.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    ladder_inputs = ladder_inputs_for_prepared(prepared)
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
        if (
            elig is not None
            and elig.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV
        ):
            if keyword_pay_for_order_exceeds_max(
                ctx, max_pay_for_order=float(max_pay_for_order)
            ):
                _append_trim_to_mode(
                    actions,
                    ks_id=ks_id,
                    current=current,
                    target=KeywordStrategyMode.OFF,
                    hard_status=hard_status,
                )
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder_inputs)
        target = _find_trim_target_mode(
            ctx,
            current,
            catalog=catalog,
            max_pay_for_order=float(max_pay_for_order),
            ladder_inputs=ladder_inputs,
            policy=policy,
            eligibility_by_ks_id=eligibility_by_ks_id,
        )
        if target == current:
            continue
        current_c = candidate_for_strategy_mode(current, catalog)
        target_c = candidate_for_strategy_mode(target, catalog)
        if mode_candidates_same_effective_target(current_c, target_c):
            logger.debug(
                "v3 skip trim kw=%s: %s and %s same target_place",
                ctx.keyword.text,
                current.name,
                target.name,
            )
            continue
        _append_trim_to_mode(
            actions,
            ks_id=ks_id,
            current=current,
            target=target,
            hard_status=hard_status,
        )
    return actions


def plan_rollout_down_one(
    prepared: PreparedList,
    *,
    reason: str,
) -> list[V3Action]:
    """Single DOWN: highest pay_for_order first (expensive → cheap)."""
    actives = _active_entries(prepared)
    actives.sort(key=lambda t: _down_sort_key(t[0]), reverse=True)
    for ctx, mode in actives:
        if int(ctx.keyword.hard_status) != _HARD_STATUS_WHITE_LIST:
            continue
        if mode == KeywordStrategyMode.OFF:
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared)
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
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        can_target_mode,
        clamp_target_mode,
    )

    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
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
        step = resolve_next_effective_step_up(current, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        if step.next_mode is None:
            continue
        to_mode = step.next_mode
        capped = (
            clamp_target_mode(elig, to_mode) if elig is not None else to_mode
        )
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


def plan_cost_reallocation(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """COST_REALLOCATION: схлопнутое итоговое действие на ключ.

    WL: один DOWN до ``final_target``; авто: FORCE_OFF (+ технический UP до
    ``final_target``, если не OFF). Активные дороже ``min(potential passing cost)``.

    Внутренний цикл: один ``resolve_next_effective_step_down`` на итерацию; alias-режимы
    с тем же ``target_place`` не увеличивают ``released_steps`` (см.
    ``count_effective_released_aggression_steps``).
    """
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    stored_by_ks: dict[int, tuple[KeywordStrategyMode, int]] = {}
    for ctx, mode in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is not None:
            stored_by_ks[int(ks_id)] = (mode, int(ctx.keyword.hard_status))

    overrides: dict[int, KeywordStrategyMode] = {}
    released_steps = 0
    for _ in range(50):
        potential_passing = collect_potential_passing_states(
            prepared,
            resolve=resolve,
            policy=policy,
            eligibility_by_ks_id=eligibility_by_ks_id,
            overrides=overrides,
            ladder_inputs=ladder,
        )
        if not potential_passing:
            break
        min_potential_cost = potential_passing[0].cost
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
        step = resolve_next_effective_step_down(
            worst_active.strategy_mode,
            catalog,
        )
        log_skipped_aliases(ctx_worst.keyword.text, step.skipped_aliases)
        if step.next_mode is None:
            break
        released = count_effective_released_aggression_steps(
            worst_active.strategy_mode,
            step.next_mode,
            catalog,
        )
        if released == 0:
            logger.debug(
                "v3 realloc hollow down kw=%s: %s -> %s same target_place, stop",
                ctx_worst.keyword.text,
                worst_active.strategy_mode.name,
                step.next_mode.name,
            )
            break
        released_steps += released
        overrides[worst_active.ks_id] = step.next_mode

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
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        can_target_mode,
        clamp_target_mode,
    )

    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    actions: list[V3Action] = []
    for ctx, current_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
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
        current_c = candidate_for_strategy_mode(current_mode, catalog)
        best_mode: KeywordStrategyMode | None = None
        best_cost: float | None = None
        best_imputed = False
        for to_mode in iter_effective_upper_modes(current_mode, catalog):
            capped = (
                clamp_target_mode(elig, to_mode)
                if elig is not None
                else to_mode
            )
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
            if best_mode is None or mode_level(capped) > mode_level(best_mode):
                best_mode = capped
                best_cost = cost
                best_imputed = imputed
        if best_mode is None or best_mode == current_mode:
            continue
        best_c = candidate_for_strategy_mode(best_mode, catalog)
        if mode_candidates_same_effective_target(current_c, best_c):
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


def plan_max_cpa_guard(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> list[V3Action]:
    """MAX_CPA_GUARD: trim только по ``plan.max_pay_for_order``."""
    actions = plan_campaign_trim_by_max_state_cost(
        prepared,
        max_pay_for_order=float(max_pay_for_order),
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
        eligibility_by_ks_id=eligibility_by_ks_id,
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
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        current_c = candidate_for_strategy_mode(current_mode, catalog)
        best_mode: KeywordStrategyMode | None = None
        best_cost: float | None = None
        best_imputed = False
        for to_mode in iter_effective_upper_modes(current_mode, catalog):
            if mode_level(to_mode) > mode_level(policy.max_target_mode):
                continue
            cost, imputed = _resolve_state_cost_for_mode(
                ctx=ctx,
                to_mode=to_mode,
                ladder_inputs=ladder,
            )
            if cost == float("inf") or cost > resolve:
                continue
            if best_mode is None or mode_level(to_mode) > mode_level(best_mode):
                best_mode = to_mode
                best_cost = cost
                best_imputed = imputed
        if best_mode is None or best_mode == current_mode:
            continue
        best_c = candidate_for_strategy_mode(best_mode, catalog)
        if mode_candidates_same_effective_target(current_c, best_c):
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
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
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
    ladder_inputs: "LadderInputs | None" = None,
    overrides: dict[int, KeywordStrategyMode] | None = None,
) -> list[_StateView]:
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        current = overrides.get(ks_id, stored_mode)
        if current == KeywordStrategyMode.OFF:
            continue
        if mode_level(current) > mode_level(policy.max_target_mode):
            continue
        cost, imputed = _resolve_state_cost_for_mode(
            ctx=ctx,
            to_mode=current,
            ladder_inputs=ladder,
        )
        if cost == float("inf") or cost <= resolve:
            continue
        out.append(
            _StateView(
                ks_id=ks_id,
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
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
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
) -> list[V3Action]:
    """M3: один UP на cheapest potential если есть headroom."""
    if fact_pay_for_order is None or fact_pay_for_order >= 0.9 * resolve:
        return []
    candidates = collect_transition_candidates(prepared, policy=policy)
    one_step = [
        c for c in candidates if mode_level(c.to_mode) == mode_level(c.from_mode) + 1
    ]
    if not one_step:
        return []
    best = min(one_step, key=lambda c: c.state_cost)
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
