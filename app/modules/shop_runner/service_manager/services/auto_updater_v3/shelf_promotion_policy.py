"""Полочная фаза V3: unified pooled ranking + rec-gate policy.

В ``UNDERPERFORM`` для полок используется то же pooled-ядро, что и вне полок.
Различия:
- rec-gate включается только при ``shelf>=organic``/``UNKNOWN``;
- до ранжирования действует фильтр target-состояний по ``aggressiveness`` 1/2/3.
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    plan_no_data_min_up_actions,
    split_prepared_by_v2_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    merge_and_dedup_actions,
    plan_overspend_actions,
    plan_rollout_down_one,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
    plan_one_up_by_policy,
    plan_shelf_rec_false_cleanup_down,
)


def _plan_underperform_shelf(
    prepared: PreparedList,
    *,
    click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
) -> list[V3Action]:
    cleanup = plan_shelf_rec_false_cleanup_down(prepared, click_mode=click_mode)
    if cleanup:
        return cleanup

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=click_mode,
        aggressiveness=aggressiveness,
    )
    return plan_one_up_by_policy(prepared, policy=policy)


def plan_shelf_promotion_actions(
    prepared: PreparedList,
    *,
    state: SalesStates,
    click_mode: ShelfClickMode,
    rollout_aggressiveness: V3RolloutAggressiveness,
    plan_max_pay_for_order: float | None = None,
) -> list[V3Action]:
    """Полочная фаза: UP/DOWN + pooled UP с rec-gate и aggr-фильтром."""
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
        return _plan_underperform_shelf(
            prepared,
            click_mode=click_mode,
            aggressiveness=rollout_aggressiveness,
        )

    if state == SalesStates.NO_DATA:
        with_cpo, without_cpo = split_prepared_by_v2_cpo(prepared)
        no_data_actions = plan_no_data_min_up_actions(without_cpo)
        if with_cpo:
            shelf_rollout = _plan_underperform_shelf(
                with_cpo,
                click_mode=click_mode,
                aggressiveness=rollout_aggressiveness,
            )
            merged = merge_and_dedup_actions(no_data_actions, shelf_rollout, [], [])
            if merged:
                return merged
        if no_data_actions:
            return no_data_actions
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="no_data_no_off_keys")]

    return [V3Action(action=V3ActionType.DO_NOTHING, reason="unknown_state")]
