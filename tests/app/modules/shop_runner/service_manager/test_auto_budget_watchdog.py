import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager


@pytest.mark.asyncio
async def test_auto_budget_watchdog_filters_campaigns_with_flag_enabled():
    wb_api = MagicMock()
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.shop_id = "test-shop"
    wb_api.session = MagicMock()

    enabled_adv_setting = MagicMock()
    enabled_adv_setting.id = 1
    enabled_adv_setting.auto_budget_watchdog_enabled = True

    disabled_adv_setting = MagicMock()
    disabled_adv_setting.id = 2
    disabled_adv_setting.auto_budget_watchdog_enabled = False

    enabled_adv = MagicMock()
    enabled_adv.auto_budget_daily_limit = 100
    enabled_adv.adv_id = 101
    enabled_adv.search_auto_budget_daily_limit = 0
    enabled_adv.search_adv_id = None
    enabled_adv.auto_budget_watchdog_enabled = True
    enabled_adv.use_common_budget = False
    enabled_adv.common_budget_daily_limit = None
    enabled_adv.adv_setting = enabled_adv_setting

    disabled_adv = MagicMock()
    disabled_adv.auto_budget_daily_limit = 100
    disabled_adv.adv_id = 202
    disabled_adv.search_auto_budget_daily_limit = 0
    disabled_adv.search_adv_id = None
    disabled_adv.auto_budget_watchdog_enabled = False
    disabled_adv.use_common_budget = False
    disabled_adv.common_budget_daily_limit = None
    disabled_adv.adv_setting = disabled_adv_setting

    wb_shop_data_manager_instance = MagicMock()
    wb_shop_data_manager_instance.get_complex_advs = AsyncMock(
        return_value=[enabled_adv, disabled_adv]
    )
    wb_shop_data_manager_instance.attach_leg_cpo = AsyncMock()

    auto_budget_service_instance = MagicMock()
    auto_budget_service_instance.ensure_budget = AsyncMock(return_value=None)
    auto_budget_service_instance.refresh_promo_state = AsyncMock()

    async def mock_run_tasks(handlers, *args, **kwargs):
        return [await handler() for handler in handlers]

    wb_manager_hub = MagicMock()

    async def mock_split_fresh(self, candidates, *, operation_name):
        return candidates, []

    with patch(
        "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
        return_value=wb_shop_data_manager_instance,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.AutoBudgetService",
        return_value=auto_budget_service_instance,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.WBManagerHubFactory.get_wb_manager_from_context",
        return_value=wb_manager_hub,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.run_tasks",
        new=mock_run_tasks,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.CoroutinesManager._split_advs_by_stats_freshness",
        new=mock_split_fresh,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.CoroutinesManager._run_auto_adv_active_control",
        new=AsyncMock(),
    ):
        plan_fact_reader = MagicMock(spec=PlanFactReader)
        plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

        fake_wb_manager_hub = MagicMock()
        fake_wb_manager_hub.wb_data_manager = MagicMock()
        fake_wb_manager_hub.wb_manager = MagicMock()

        coroutines_manager = CoroutinesManager(
            wb_api,
            MagicMock(),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=plan_fact_reader,
            wb_manager_hub=fake_wb_manager_hub,
        )
        await coroutines_manager.auto_budget_watchdog.__wrapped__(coroutines_manager, only_bot_active=True)

    wb_shop_data_manager_instance.attach_leg_cpo.assert_awaited_once_with(
        [enabled_adv, disabled_adv]
    )
    auto_budget_service_instance.ensure_budget.assert_called_once()
    called_args = auto_budget_service_instance.ensure_budget.call_args[0]
    assert called_args[0] == enabled_adv
    assert called_args[1] == enabled_adv_setting.id
    auto_budget_service_instance.ensure_common_budget.assert_not_called()


@pytest.mark.asyncio
async def test_auto_budget_watchdog_common_mode_calls_ensure_common_budget():
    wb_api = MagicMock()
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.shop_id = "test-shop"
    wb_api.session = MagicMock()

    adv_setting = MagicMock()
    adv_setting.id = 1

    common_adv = MagicMock()
    common_adv.auto_budget_daily_limit = 0
    common_adv.search_auto_budget_daily_limit = 0
    common_adv.adv_id = 101
    common_adv.search_adv_id = 102
    common_adv.auto_budget_watchdog_enabled = True
    common_adv.use_common_budget = True
    common_adv.common_budget_daily_limit = 500
    common_adv.adv_setting = adv_setting

    wb_shop_data_manager_instance = MagicMock()
    wb_shop_data_manager_instance.get_complex_advs = AsyncMock(
        return_value=[common_adv]
    )
    wb_shop_data_manager_instance.attach_leg_cpo = AsyncMock()

    auto_budget_service_instance = MagicMock()
    auto_budget_service_instance.ensure_budget = AsyncMock(return_value=None)
    auto_budget_service_instance.ensure_common_budget = AsyncMock(return_value=None)
    auto_budget_service_instance.refresh_promo_state = AsyncMock()

    async def mock_run_tasks(handlers, *args, **kwargs):
        return [await handler() for handler in handlers]

    wb_manager_hub = MagicMock()
    async def mock_split_fresh(self, candidates, *, operation_name):
        return candidates, []

    with patch(
        "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
        return_value=wb_shop_data_manager_instance,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.AutoBudgetService",
        return_value=auto_budget_service_instance,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.WBManagerHubFactory.get_wb_manager_from_context",
        return_value=wb_manager_hub,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.run_tasks",
        new=mock_run_tasks,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.CoroutinesManager._split_advs_by_stats_freshness",
        new=mock_split_fresh,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.CoroutinesManager._run_auto_adv_active_control",
        new=AsyncMock(),
    ):
        plan_fact_reader = MagicMock(spec=PlanFactReader)
        plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

        fake_wb_manager_hub = MagicMock()
        fake_wb_manager_hub.wb_data_manager = MagicMock()
        fake_wb_manager_hub.wb_manager = MagicMock()

        coroutines_manager = CoroutinesManager(
            wb_api,
            MagicMock(),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=plan_fact_reader,
            wb_manager_hub=fake_wb_manager_hub,
        )
        await coroutines_manager.auto_budget_watchdog.__wrapped__(coroutines_manager, only_bot_active=True)

    wb_shop_data_manager_instance.attach_leg_cpo.assert_awaited_once_with([common_adv])
    auto_budget_service_instance.ensure_common_budget.assert_called_once()
    called_args = auto_budget_service_instance.ensure_common_budget.call_args[0]
    assert called_args[0] == common_adv
    assert called_args[1] == adv_setting.id
    auto_budget_service_instance.ensure_budget.assert_not_called()


@pytest.mark.asyncio
async def test_auto_budget_watchdog_runs_active_control_without_budget_handlers():
    """Нет кандидатов на автобюджет — ensure не вызывается, контроль активности всё равно один раз."""
    wb_api = MagicMock()
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.shop_id = "test-shop"
    wb_api.session = MagicMock()

    adv_setting = MagicMock()
    adv_setting.id = 99

    # Включён watchdog, но лимиты 0 — не попадает в handlers
    adv = MagicMock()
    adv.auto_budget_daily_limit = 0
    adv.search_auto_budget_daily_limit = 0
    adv.adv_id = 101
    adv.search_adv_id = None
    adv.auto_budget_watchdog_enabled = True
    adv.use_common_budget = False
    adv.common_budget_daily_limit = 0
    adv.adv_setting = adv_setting

    wb_shop_data_manager_instance = MagicMock()
    wb_shop_data_manager_instance.get_complex_advs = AsyncMock(return_value=[adv])
    wb_shop_data_manager_instance.attach_leg_cpo = AsyncMock()

    auto_budget_service_instance = MagicMock()
    auto_budget_service_instance.ensure_budget = AsyncMock(return_value=None)
    auto_budget_service_instance.ensure_common_budget = AsyncMock(return_value=None)
    auto_budget_service_instance.refresh_promo_state = AsyncMock()

    active_control = AsyncMock()
    wb_manager_hub = MagicMock()

    async def mock_split_fresh(self, candidates, *, operation_name):
        return candidates, []

    with patch(
        "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
        return_value=wb_shop_data_manager_instance,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.AutoBudgetService",
        return_value=auto_budget_service_instance,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.WBManagerHubFactory.get_wb_manager_from_context",
        return_value=wb_manager_hub,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.CoroutinesManager._split_advs_by_stats_freshness",
        new=mock_split_fresh,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.CoroutinesManager._run_auto_adv_active_control",
        new=active_control,
    ):
        plan_fact_reader = MagicMock(spec=PlanFactReader)
        plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

        fake_wb_manager_hub = MagicMock()
        fake_wb_manager_hub.wb_data_manager = MagicMock()
        fake_wb_manager_hub.wb_manager = MagicMock()

        coroutines_manager = CoroutinesManager(
            wb_api,
            MagicMock(),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=plan_fact_reader,
            wb_manager_hub=fake_wb_manager_hub,
        )
        await coroutines_manager.auto_budget_watchdog.__wrapped__(coroutines_manager, only_bot_active=True)

    wb_shop_data_manager_instance.attach_leg_cpo.assert_awaited_once_with([adv])
    auto_budget_service_instance.ensure_budget.assert_not_called()
    auto_budget_service_instance.ensure_common_budget.assert_not_called()
    active_control.assert_awaited_once()
