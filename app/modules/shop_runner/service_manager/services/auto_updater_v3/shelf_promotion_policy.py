"""Полочная фаза V3: ``rec_system_mode`` + авто ``started``.

Почему стратегии отличаются: ``auto_updater_traffic_policy``.

Decision matrix (UNDERPERFORM), механика выбора:
- ``organic > shelf`` → **послойная** + aggr=MIN, cost-first по upper states.
- ``shelf >= organic`` или DTO нет → **поштучная**: shelf pending, затем non-shelf;
  ``aggressiveness`` (1/2/3) в этой ветке **не используется**.

Отдельно от ``AdvSetting.strategy`` (MIN_CPO/MAX_CONV).
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ActivationStrategy,
    ShelfClickMode,
    activation_strategy_for_shelf_underperform,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_overspend_actions,
    plan_rollout_down_one,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    plan_cost_first_up_one,
    plan_shelf_rec_false_cleanup_down,
)


def _plan_underperform_shelf(
    prepared: PreparedList,
    *,
    click_mode: ShelfClickMode,
) -> list[V3Action]:
    cleanup = plan_shelf_rec_false_cleanup_down(prepared, click_mode=click_mode)
    if cleanup is not None:
        return cleanup

    strategy = activation_strategy_for_shelf_underperform(click_mode)
    if strategy == ActivationStrategy.LAYERED:
        return plan_cost_first_up_one(
            prepared,
            click_mode=click_mode,
            layered=True,
            aggressiveness=V3RolloutAggressiveness.MIN,
            piecewise_shelf=False,
        )
    return plan_cost_first_up_one(
        prepared,
        click_mode=click_mode,
        layered=False,
        aggressiveness=V3RolloutAggressiveness.MIN,
        piecewise_shelf=True,
    )


def plan_shelf_promotion_actions(
    prepared: PreparedList,
    *,
    state: SalesStates,
    click_mode: ShelfClickMode,
    plan_max_pay_for_order: float | None = None,
) -> list[V3Action]:
    """Полочная фаза: UP/DOWN без 1–2–3 rollout; underperform по click_mode."""
    if state == SalesStates.OPTIMAL:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="optimal")]

    if state == SalesStates.OVERSPEND:
        if plan_max_pay_for_order is not None:
            return plan_overspend_actions(
                prepared, max_pay_for_order=float(plan_max_pay_for_order)
            )
        return plan_rollout_down_one(prepared, reason="overspend")

    if state == SalesStates.STABLE:
        return plan_rollout_down_one(prepared, reason="stable")

    if state == SalesStates.UNDERPERFORM:
        return _plan_underperform_shelf(prepared, click_mode=click_mode)

    return [V3Action(action=V3ActionType.DO_NOTHING, reason="unknown_state")]
