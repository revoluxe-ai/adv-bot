"""Select UP/DOWN actions from campaign state and per-keyword v3 context.

Signal matrix (v3):
- Plan/fact unchanged short-circuit in orchestrator.
- ``SalesStates`` from ``detect_campaign_state`` — global economy (OPTIMAL / UNDERPERFORM / …).
- Полочная фаза: ``rec_system_mode`` + авто ``started`` → ``plan_shelf_promotion_actions``
  с ``ShelfClickMode`` (organic/shelf клики). Иначе — ``RolloutPlanner`` + ``aggressiveness``.

Стратегия активации:
- Единый pooled-UP в shelf/non-shelf с фильтром target по ``aggressiveness`` (1/2/3).
- Rec-gate включается только в shelf-dominant режиме (``shelf>=organic``/``UNKNOWN``).

При **OVERSPEND** (факт > ``max_pay_for_order``): сначала массовый ``FORCE_OFF`` для всех
активных ключей с ``pay_for_order > max``; иначе один DOWN (``plan_rollout_down_one``).

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
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    build_worst_costs,
    compute_resolve_cost_threshold,
    is_resolve_valid,
    merge_and_dedup_actions,
    plan_headroom_plus_one,
    plan_mass_cheap_promotion,
    plan_overspend_actions,
    plan_rollout_down_one,
    plan_rollout_underperform_one,
    plan_state_rebalance,
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
    """Return planned mode changes for one cycle (OVERSPEND may return several FORCE_OFF)."""
    prepared: PreparedList = []
    for ctx in contexts:
        mode = stored_strategy_mode(ctx.keyword)
        prepared.append((ctx, mode))

    aggr = normalize_v3_rollout_aggressiveness(rollout_aggressiveness)

    if plan is not None and fact is not None:
        resolve = compute_resolve_cost_threshold(plan, fact)
        if not is_resolve_valid(plan, resolve):
            return [V3Action(action=V3ActionType.DO_NOTHING, reason="skip_invalid_resolve")]

        # Главный путь orchestrator всегда передаёт plan/fact; OVERSPEND обрабатываем
        # до M1/M2/M3 (массовый FORCE_OFF по ключам выше max).
        if state == SalesStates.OVERSPEND:
            max_pfo = plan_max_pay_for_order
            if max_pfo is None:
                max_pfo = float(plan.max_pay_for_order)
            return plan_overspend_actions(
                prepared, max_pay_for_order=float(max_pfo)
            )

        click_mode = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
        policy = SelectionPolicy.from_aggressiveness(
            click_mode=click_mode,
            aggressiveness=aggr,
        )

        cleanup_actions: list[V3Action] = []
        if shelf_promotion_active:
            cleanup_actions = plan_shelf_rec_false_cleanup_down(
                prepared, click_mode=click_mode
            )

        worst_costs = build_worst_costs(prepared)
        m1_actions = plan_mass_cheap_promotion(
            prepared,
            resolve=resolve,
            policy=policy,
            worst_costs=worst_costs,
        )
        m2_actions = plan_state_rebalance(
            prepared,
            resolve=resolve,
            policy=policy,
            worst_costs=worst_costs,
        )
        m3_actions = plan_headroom_plus_one(
            prepared,
            resolve=resolve,
            fact_pay_for_order=(
                float(fact.pay_for_order) if fact.pay_for_order is not None else None
            ),
            policy=policy,
        )
        merged = merge_and_dedup_actions(
            cleanup_actions, m1_actions, m2_actions, m3_actions
        )
        if merged:
            return merged
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="no_actions")]

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
