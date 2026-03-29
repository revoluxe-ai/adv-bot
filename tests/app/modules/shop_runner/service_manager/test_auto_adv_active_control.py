from datetime import date
from typing import Awaitable, Callable

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    PlanFactSummary,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

_SERVICE_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_adv_active_control.auto_adv_active_control_service"
)


@pytest.fixture(autouse=True)
def _mock_positive_cabinet_balance() -> object:
    """Тесты не ходят в БД за балансом кабинета; иначе _cabinet_has_positive_balance даёт False."""
    with patch.object(
        AutoAdvActiveControlService,
        "_cabinet_has_positive_balance",
        new=AsyncMock(return_value=True),
    ):
        yield


async def _mock_load_time_settings_for_adv_ids(session, adv_ids):
    """Мок загрузки настроек времени: без ограничений (None) для всех adv_setting_id."""
    return {aid: None for aid in adv_ids}


class _FakeAdvSetting:
    def __init__(
        self,
        active_status: str,
        adv_id: int | None = None,
        *,
        adv_setting_id: int | None = None,
        wb_cabinet_id: int = 1,
        plan_for_sales_for_day: int | None = None,
        target_price_for_order: int | float | None = None,
        max_price_for_order: int | float | None = None,
        rec_system_mode: bool = True,
    ):
        self.active_status = active_status
        self.adv_id = adv_id
        self.wb_cabinet_id = wb_cabinet_id
        self.id = adv_setting_id if adv_setting_id is not None else (adv_id if adv_id is not None else 0)
        self.plan_for_sales_for_day = plan_for_sales_for_day
        self.target_price_for_order = target_price_for_order
        self.max_price_for_order = max_price_for_order
        self.rec_system_mode = rec_system_mode


class _FakeSearchAdv:
    def __init__(self, active_status: str, adv_id: int | None = None):
        self.active_status = active_status
        self.adv_id = adv_id


class _FakeComplexAdv:
    def __init__(
        self,
        auto_limit: int,
        auto_status: str,
        search_limit: int,
        search_status: str,
        auto_adv_id: int | None = None,
        search_adv_id: int | None = None,
        *,
        bot_active: bool = True,
        watchdog_enabled: bool = True,
        use_common_budget: bool = False,
        common_budget_daily_limit: int | None = None,
        plan_for_sales_for_day: int | None = None,
        target_price_for_order: int | float | None = None,
        max_price_for_order: int | float | None = None,
        rec_system_mode: bool = True,
    ):
        self.bot_active = bot_active
        self.auto_budget_watchdog_enabled = watchdog_enabled
        self._auto_budget_daily_limit = auto_limit
        self._search_auto_budget_daily_limit = search_limit
        self._adv_setting = _FakeAdvSetting(
            active_status=auto_status,
            adv_id=auto_adv_id,
            plan_for_sales_for_day=plan_for_sales_for_day,
            target_price_for_order=target_price_for_order,
            max_price_for_order=max_price_for_order,
            rec_system_mode=rec_system_mode,
        )
        self.search_adv = _FakeSearchAdv(active_status=search_status, adv_id=search_adv_id)
        self.shop_id = "shop-1"
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = search_adv_id
        self.auto_adv_active_status_str = WBAdvActiveStatus(auto_status)
        self.search_adv_active_status_str = WBAdvActiveStatus(search_status)
        self._use_common_budget = use_common_budget
        self._common_budget_daily_limit = common_budget_daily_limit

    @property
    def adv_setting(self):
        return self._adv_setting

    @property
    def auto_budget_daily_limit(self) -> int:
        return self._auto_budget_daily_limit

    @property
    def search_auto_budget_daily_limit(self) -> int:
        return self._search_auto_budget_daily_limit

    @property
    def use_common_budget(self) -> bool:
        return self._use_common_budget

    @property
    def common_budget_daily_limit(self) -> int | None:
        return self._common_budget_daily_limit

    @property
    def rec_system_promotion_mode_active(self) -> bool:
        return self._adv_setting.rec_system_mode


@pytest.mark.asyncio
async def test_auto_adv_active_control_service_starts_and_pauses_campaigns():
    adv_to_start = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=50,
        search_status="pause",
        auto_adv_id=1,
        search_adv_id=2,
        plan_for_sales_for_day=1,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    adv_to_pause = _FakeComplexAdv(
        auto_limit=0,
        auto_status="started",
        search_limit=0,
        search_status="started",
        auto_adv_id=3,
        search_adv_id=4,
    )
    ignored_adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=0,
        search_status="started",
        auto_adv_id=5,
        search_adv_id=6,
        watchdog_enabled=False,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    run_tasks_call: dict[str, object] = {}

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        run_tasks_call["tasks_manager"] = kwargs.get("tasks_manager")
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(side_effect=lambda adv_id: plan_fact_for(adv_id))
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    async def mock_spend(*args, **kwargs):
        adv_id = args[0]
        return 0.0

    def plan_fact_for(adv_id):
        mapping = {
            1: PlanFactSummary(
                adv_id=1,
                plan_orders=1,
                plan_target_pay_for_order=100,
                plan_max_pay_for_order=200,
                fact_predict_orders=2.0,
                fact_pay_for_order=150.0,
            ),
            3: PlanFactSummary(
                adv_id=3,
                plan_orders=1,
                plan_target_pay_for_order=100,
                plan_max_pay_for_order=200,
                fact_predict_orders=2.0,
                fact_pay_for_order=150.0,
            ),
            5: PlanFactSummary(
                adv_id=5,
                plan_orders=1,
                plan_target_pay_for_order=100,
                plan_max_pay_for_order=200,
                fact_predict_orders=2.0,
                fact_pay_for_order=150.0,
            ),
        }
        return mapping.get(adv_id)

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(side_effect=mock_spend),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active(
            [adv_to_start, adv_to_pause, ignored_adv]
        )

    wb_modifier.start_auto_campaign.assert_awaited_once_with(adv_to_start)
    wb_modifier.start_auction_campaign.assert_awaited_once_with(adv_to_start)
    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv_to_pause)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv_to_pause)
    assert run_tasks_call["tasks_manager"] is tasks_manager


@pytest.mark.asyncio
async def test_auto_adv_active_control_pauses_auto_campaign_when_rec_system_mode_off():
    """When rec_system (shelf promotion) mode is off, auto campaign is paused and not started."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=50,
        search_status="pause",
        auto_adv_id=10,
        search_adv_id=11,
        rec_system_mode=False,
    )
    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        for handler in handlers:
            await handler()
        return []

    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(spec=PlanFactReader),
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_adv_active_control_service_pauses_when_daily_limit_exceeded():
    overspend_adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=80,
        search_status="started",
        auto_adv_id=7,
        search_adv_id=8,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=7,
            plan_orders=1,
            plan_target_pay_for_order=100,
            plan_max_pay_for_order=200,
            fact_predict_orders=0.0,
            fact_pay_for_order=0.0,
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    async def mock_spend(*args, **kwargs):
        adv_id = args[0]
        return 150.0 if adv_id == 7 else 200.0

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(side_effect=mock_spend),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([overspend_adv])

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(overspend_adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(overspend_adv)
    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.start_auction_campaign.assert_not_called()




@pytest.mark.asyncio
async def test_auto_adv_active_control_common_budget_pauses_when_combined_spend_exceeds_limit():
    """При общем бюджете обе кампании ставятся на паузу, если суммарный расход >= лимита."""
    adv = _FakeComplexAdv(
        auto_limit=0,
        auto_status="started",
        search_limit=0,
        search_status="started",
        auto_adv_id=11,
        search_adv_id=12,
        use_common_budget=True,
        common_budget_daily_limit=200,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        for handler in handlers:
            await handler()
        return []

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    async def mock_spend(*args, **kwargs):
        # auto_adv_id=11 -> 100, search_adv_id=12 -> 150, combined=250 >= 200
        adv_id = args[0]
        return 100.0 if adv_id == 11 else 150.0

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(side_effect=mock_spend),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.start_auction_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_active_control_common_budget_starts_when_under_limit():
    """При общем бюджете обе кампании запускаются, если суммарный расход < лимита и правило себестоимости выполняется."""
    adv = _FakeComplexAdv(
        auto_limit=0,
        auto_status="pause",
        search_limit=0,
        search_status="pause",
        auto_adv_id=13,
        search_adv_id=14,
        use_common_budget=True,
        common_budget_daily_limit=500,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        for handler in handlers:
            await handler()
        return []

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=13,
            plan_orders=10,
            plan_target_pay_for_order=100,
            plan_max_pay_for_order=200,
            fact_predict_orders=12.0,
            fact_pay_for_order=90.0,
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    async def mock_spend(*args, **kwargs):
        return 50.0

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(side_effect=mock_spend),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.start_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auction_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.pause_auction_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_avg_cost_pauses_when_above_target():
    adv = _FakeComplexAdv(
        auto_limit=0,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=10,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=10,
            plan_orders=10,
            plan_target_pay_for_order=100,
            plan_max_pay_for_order=200,
            fact_predict_orders=12.0,
            fact_pay_for_order=120.0,
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_avg_cost_starts_when_below_target():
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=0,
        search_status="pause",
        auto_adv_id=11,
        plan_for_sales_for_day=10,
        target_price_for_order=120,
        max_price_for_order=220,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=11,
            plan_orders=10,
            plan_target_pay_for_order=120,
            plan_max_pay_for_order=220,
            fact_predict_orders=15.0,
            fact_pay_for_order=110.0,
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.start_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_does_not_start_when_avg_cost_above_target():
    """Separate budget: PAUSE, budget OK, but avg_cost > target_cost -> start not called."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=0,
        search_status="pause",
        auto_adv_id=20,
        search_adv_id=21,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=20,
            plan_orders=10,
            plan_target_pay_for_order=100,
            plan_max_pay_for_order=200,
            fact_predict_orders=15.0,
            fact_pay_for_order=110.0,
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=50.0),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_does_not_start_when_no_plan_fact():
    """Separate budget: PAUSE, budget OK, but plan_fact returns None -> start not called."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=0,
        search_status="pause",
        auto_adv_id=22,
        search_adv_id=23,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=50.0),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_common_budget_does_not_start_when_avg_cost_above_target():
    """Common budget: PAUSE, budget OK, but avg_cost > target_cost -> auto campaign not started."""
    adv = _FakeComplexAdv(
        auto_limit=0,
        auto_status="pause",
        search_limit=0,
        search_status="pause",
        auto_adv_id=24,
        search_adv_id=25,
        use_common_budget=True,
        common_budget_daily_limit=500,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        for handler in handlers:
            await handler()
        return []

    tasks_manager = MagicMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=24,
            plan_orders=10,
            plan_target_pay_for_order=100,
            plan_max_pay_for_order=200,
            fact_predict_orders=12.0,
            fact_pay_for_order=90.0,
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=tasks_manager,
        plan_fact_reader=plan_fact_reader,
    )

    async def mock_spend(*args, **kwargs):
        return 50.0

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(side_effect=mock_spend),
    ), patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.start_auction_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.pause_auction_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_average_order_cost_uses_additional_views():
    from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
        full_wb_adv_stat,
    )

    stats = SmallFullAdvStat(
        views=0,
        clicks=0,
        spend=1000.0,
        added_to_cart=0,
        orders=10,
        sum_price=0.0,
    )
    orders_kw = 4

    with patch(
        "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_stats_by_last_days",
        new=AsyncMock(return_value=stats),
    ) as stats_mock, patch(
        "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_keywords_spend",
        new=AsyncMock(return_value=400.0),
    ) as spend_mock, patch(
        "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_keywords_views_orders_by_days",
        new=AsyncMock(return_value={date(2025, 1, 1): (10, orders_kw)}),
    ) as views_orders_mock:
        result = await full_wb_adv_stat.get_additional_cost_per_order_for_adv(
            adv_id=42, days=6
        )

    assert result == pytest.approx((1000.0 - 400.0) / max(1, 10 - orders_kw))
    stats_mock.assert_awaited_once()
    spend_mock.assert_awaited_once()
    views_orders_mock.assert_awaited_once()
