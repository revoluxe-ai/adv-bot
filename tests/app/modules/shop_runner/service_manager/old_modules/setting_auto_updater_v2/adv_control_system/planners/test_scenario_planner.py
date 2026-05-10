"""Unit tests for ScenarioPlanner executor ordering."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.target_place_executor.target_place_down_executor import (
    TargetPlaceDownExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.target_place_executor.target_place_up_executor import (
    TargetPlaceUpExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.white_list_executor.white_list_add_executor import (
    WhiteListAddExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.white_list_executor.white_list_remove_executor import (
    WhiteListRemoveExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.planners.scenario_planner import (
    ScenarioPlanner,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)

pytestmark = pytest.mark.unit


def _types(chain: list[object]) -> list[type]:
    return [type(e) for e in chain]


def test_scenario_planner_overspend_chain_order() -> None:
    planner = ScenarioPlanner()
    chain = planner.scenarios[SalesStates.OVERSPEND]
    assert _types(chain) == [WhiteListRemoveExecutor, TargetPlaceDownExecutor]


def test_scenario_planner_underperform_chain_order() -> None:
    planner = ScenarioPlanner()
    chain = planner.scenarios[SalesStates.UNDERPERFORM]
    assert _types(chain) == [TargetPlaceUpExecutor, WhiteListAddExecutor]


def test_scenario_planner_stable_chain_order() -> None:
    planner = ScenarioPlanner()
    chain = planner.scenarios[SalesStates.STABLE]
    assert _types(chain) == [TargetPlaceDownExecutor, WhiteListRemoveExecutor]


def test_scenario_planner_optimal_empty_chain() -> None:
    planner = ScenarioPlanner()
    assert planner.scenarios[SalesStates.OPTIMAL] == []
