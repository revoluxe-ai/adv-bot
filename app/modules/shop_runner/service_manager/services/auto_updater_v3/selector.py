"""Select UP/DOWN actions from campaign state and per-keyword v3 context.

Signal matrix (v3):
- Preamble (bootstrap → realloc → expansion → guard) — в orchestrator до cache gate.
- Post-gate selector: **только shelf cleanup** (FINAL_TUNING / M3 disabled на MVP).

``AdvSetting.strategy`` (MIN_CPO/MAX_CONV) — отдельный контур ``change_adv_strategy``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    build_worst_costs,
    compute_resolve_cost_threshold,
    is_resolve_valid,
    plan_mass_cheap_promotion,
    plan_overspend_actions,
    plan_rollout_down_one,
    plan_rollout_underperform_one,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.shelf_promotion_policy import (
    plan_shelf_promotion_actions,  # legacy wrapper
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
    plan_shelf_rec_false_cleanup_down,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)

@dataclass(frozen=True)
class KeywordV3Context:
    keyword: CalculatedKeyword
    position_profile: list[PositionProfilePoint] | None


def build_prepared_from_contexts(
    contexts: list[KeywordV3Context],
) -> PreparedList:
    """Собрать ``PreparedList`` для preamble (M1/trim) и selector."""
    prepared: PreparedList = []
    for ctx in contexts:
        prepared.append((ctx, stored_strategy_mode(ctx.keyword)))
    return prepared


def plan_m1_mass_cheap_promotion_with_plan_fact(
    contexts: list[KeywordV3Context],
    *,
    plan: PlanData,
    fact: FactData,
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode | None,
    aggr: V3RolloutAggressiveness | int | None = None,
) -> list[V3Action]:
    """M1: UP каждого ключа до наивысшего M/O/C с ``state_cost <= resolve``."""
    _ = shelf_promotion_active
    prepared = build_prepared_from_contexts(contexts)
    resolve = compute_resolve_cost_threshold(plan, fact)
    if not is_resolve_valid(plan, resolve):
        return []

    click_mode = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=click_mode,
        aggressiveness=normalize_v3_rollout_aggressiveness(aggr),
    )
    worst_costs = build_worst_costs(prepared)
    return plan_mass_cheap_promotion(
        prepared,
        resolve=resolve,
        policy=policy,
        worst_costs=worst_costs,
    )


def select_v3_post_gate_actions(
    *,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode | None = None,
) -> list[V3Action]:
    """Post-gate: shelf rec-false cleanup only (без M2/M3/FINAL_TUNING)."""
    if not shelf_promotion_active:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="post_gate_no_shelf")]
    prepared = build_prepared_from_contexts(contexts)
    click_mode = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
    cleanup = plan_shelf_rec_false_cleanup_down(prepared, click_mode=click_mode)
    if cleanup:
        return cleanup
    return [V3Action(action=V3ActionType.DO_NOTHING, reason="post_gate_no_actions")]


def select_v3_actions(
    *,
    state: SalesStates,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    rollout_aggressiveness: int | None = None,
    shelf_click_mode: ShelfClickMode | None = None,
    plan_max_pay_for_order: float | None = None,
    plan: PlanData | None = None,
    fact: FactData | None = None,
) -> list[V3Action]:
    """Legacy selector; при plan/fact делегирует в post-gate (shelf only)."""
    if plan is not None and fact is not None:
        if state == SalesStates.NO_DATA:
            return [
                V3Action(
                    action=V3ActionType.DO_NOTHING,
                    reason="campaign_no_data_wait",
                )
            ]
        return select_v3_post_gate_actions(
            contexts=contexts,
            shelf_promotion_active=shelf_promotion_active,
            shelf_click_mode=shelf_click_mode,
        )

    prepared = build_prepared_from_contexts(contexts)
    aggr = normalize_v3_rollout_aggressiveness(rollout_aggressiveness)

    if shelf_promotion_active:
        click_mode = (
            shelf_click_mode
            if shelf_click_mode is not None
            else ShelfClickMode.UNKNOWN
        )
        return plan_shelf_promotion_actions(
            prepared,
            state=state,
            click_mode=click_mode,
            rollout_aggressiveness=aggr,
            plan_max_pay_for_order=plan_max_pay_for_order,
        )

    if state == SalesStates.OPTIMAL:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="optimal")]

    if state == SalesStates.NO_DATA:
        return [
            V3Action(
                action=V3ActionType.DO_NOTHING,
                reason="campaign_no_data_wait",
            )
        ]

    if state == SalesStates.OVERSPEND:
        if plan_max_pay_for_order is not None:
            return plan_overspend_actions(
                prepared, max_pay_for_order=float(plan_max_pay_for_order)
            )
        return plan_rollout_down_one(prepared, reason="overspend")

    if state == SalesStates.UNDERPERFORM:
        return plan_rollout_underperform_one(prepared, aggr)

    if state == SalesStates.STABLE:
        return plan_rollout_down_one(prepared, reason="stable")

    return [V3Action(action=V3ActionType.DO_NOTHING, reason="unknown_state")]
