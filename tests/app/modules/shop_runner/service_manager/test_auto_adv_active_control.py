"""Unit coverage for empty-keywords pause and auto active control behavior."""

import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidSelectedCpoContract,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    AuctionReasonCode,
    AutoReasonCode,
    CampaignActivityCommand,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

_SERVICE_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_adv_active_control.auto_adv_active_control_service"
)


async def _run_tasks_for_tests(
    handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs
) -> list[object]:
    results = []
    for handler in handlers:
        results.append(await handler())
    return results


@pytest.fixture(autouse=True)
def _positive_cabinet_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Избегаем реального balance_manager: положительный баланс кабинета."""
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )


@pytest.fixture(autouse=True)
def _empty_keywords_intent_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Baseline suite: empty-keywords intent отсутствует (нет реального Redis)."""
    intent_cls = (
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager"
    )
    monkeypatch.setattr(f"{intent_cls}.consume_intent", AsyncMock(return_value=False))
    monkeypatch.setattr(f"{intent_cls}.peek_intent", AsyncMock(return_value=False))
    monkeypatch.setattr(f"{intent_cls}.set_intent", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.decision.is_warmup_false_empty_keywords",
        AsyncMock(return_value=False),
    )


@pytest.fixture(autouse=True)
def _shelf_exhausted_pg_block_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Baseline suite: PG our-block shelf-exhausted отсутствует (нет реального PG)."""
    repo = (
        "app.modules.shop_runner.service_manager.services."
        "auto_shelf_bid_control_manager.auto_shelf_bid_control_repository."
        "AutoShelfBidControlRepository"
    )
    monkeypatch.setattr(f"{repo}.get_state", AsyncMock(return_value=None))
    monkeypatch.setattr(
        f"{repo}.mark_shelf_exhausted_epoch_started",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        f"{repo}.mark_shelf_exhausted_notify_sent",
        AsyncMock(return_value=None),
    )

    class _FakeSessionCM:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *args):
            return False

    def _fake_sm(*args, **kwargs):
        return _FakeSessionCM()

    monkeypatch.setattr(f"{_SERVICE_MODULE}.get_session_maker", _fake_sm)


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
        plan_for_sales_for_day: Any = None,
        target_price_for_order: Any = None,
        max_price_for_order: Any = None,
        rec_system_mode: bool = True,
        auto_shelf_bid_control_enabled: bool = False,
        bidder_coroutine_type: BidderCoroutineType = (
            BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
        ),
    ):
        self.active_status = active_status
        self.adv_id = adv_id
        self.id = adv_setting_id if adv_setting_id is not None else (adv_id if adv_id is not None else 0)
        self.wb_cabinet_id = wb_cabinet_id
        self.plan_for_sales_for_day = plan_for_sales_for_day
        self.target_price_for_order = target_price_for_order
        self.max_price_for_order = max_price_for_order
        self.rec_system_mode = rec_system_mode
        self.sales_predict_method = FactMethods.DIRECT_SALES
        self.auto_shelf_bid_control_enabled = auto_shelf_bid_control_enabled
        self.bidder_coroutine_type = bidder_coroutine_type


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
        auto_budget_total_limit: int = 0,
        search_auto_budget_total_limit: int = 0,
        common_budget_total_limit: int = 0,
        plan_for_sales_for_day: Any = None,
        target_price_for_order: Any = None,
        max_price_for_order: Any = None,
        rec_system_mode: bool = True,
        auto_adv_bid_control_enable: bool = False,
        auto_shelf_bid_control_enabled: bool = False,
        bidder_coroutine_type: BidderCoroutineType = (
            BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
        ),
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
            auto_shelf_bid_control_enabled=auto_shelf_bid_control_enabled,
            bidder_coroutine_type=bidder_coroutine_type,
        )
        self.search_adv = _FakeSearchAdv(active_status=search_status, adv_id=search_adv_id)
        self.shop_id = "shop-1"
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = search_adv_id
        self.main_nmid = 10001
        self.nmids = [10001]
        self.auto_adv_active_status_str = WBAdvActiveStatus(auto_status)
        self.search_adv_active_status_str = WBAdvActiveStatus(search_status)
        self._use_common_budget = use_common_budget
        self._common_budget_daily_limit = common_budget_daily_limit
        self._auto_budget_total_limit = auto_budget_total_limit
        self._search_auto_budget_total_limit = search_auto_budget_total_limit
        self._common_budget_total_limit = common_budget_total_limit
        self.auto_adv_bid_control_enable = auto_adv_bid_control_enable

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
    def auto_budget_total_limit(self) -> int:
        return self._auto_budget_total_limit

    @property
    def search_auto_budget_total_limit(self) -> int:
        return self._search_auto_budget_total_limit

    @property
    def common_budget_total_limit(self) -> int:
        return self._common_budget_total_limit

    @property
    def rec_system_promotion_mode_active(self) -> bool:
        return self._adv_setting.rec_system_mode

    async def get_keywords(self) -> list[object]:
        """Stub for empty-keywords drain after mid-cycle cost skip (shelf ON)."""
        return []


async def _run_auto_cost_rule_case(
    *,
    auto_status: str = "started",
    avg_cost: object,
    fact_pay_for_order: object,
    fact_predict_orders: object = 12.0,
    resolved_target_cost: object = 100,
    auto_shelf_bid_control_enabled: bool = False,
    selected_cpo_contract: AutoShelfBidSelectedCpoContract | None = None,
) -> MagicMock:
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status=auto_status,
        search_limit=0,
        search_status="pause",
        auto_adv_id=1001,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=auto_shelf_bid_control_enabled,
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

    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=1001,
            fact_predict_orders=fact_predict_orders,  # type: ignore[arg-type]
            fact_pay_for_order=fact_pay_for_order,  # type: ignore[arg-type]
        )
    )
    reason_manager = MagicMock()
    reason_manager.set = AsyncMock()
    selected_cpo_provider = None
    if selected_cpo_contract is not None:
        selected_cpo_provider = MagicMock()
        selected_cpo_provider.build_view = AsyncMock(
            return_value=SimpleNamespace(
                enabled=True,
                expected_enforced_bid_minor=selected_cpo_contract.selected_bid_minor,
                actual_bid_minor=selected_cpo_contract.selected_bid_minor,
                bid_sync_detail="synced",
                state_updated_at=selected_cpo_contract.updated_at,
                rec_bid_recommendation={
                    "plan_ranked": [
                        {
                            "bid": selected_cpo_contract.selected_bid_minor,
                            "cpo_rub": selected_cpo_contract.selected_cpo_rub,
                        }
                    ]
                },
                best_cpo_bid_rub=selected_cpo_contract.selected_cpo_rub,
            )
        )
        selected_cpo_provider.build_selected_cpo_contract = AsyncMock(
            return_value=selected_cpo_contract
        )
    legacy_avg_cost_mock = AsyncMock(return_value=avg_cost)
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=selected_cpo_provider,
        redis_campaign_activity_reason_manager=reason_manager,
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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=legacy_avg_cost_mock,
    ), patch(
        f"{_SERVICE_MODULE}.resolve_target_cost",
        return_value=resolved_target_cost,
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.reason_manager = reason_manager
    wb_modifier.selected_cpo_provider = selected_cpo_provider
    wb_modifier.legacy_avg_cost_mock = legacy_avg_cost_mock
    return wb_modifier


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
        auto_adv_bid_control_enable=False,
        auto_shelf_bid_control_enabled=True
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
                fact_predict_orders=2.0,
                fact_pay_for_order=150.0,
            ),
            3: PlanFactSummary(
                adv_id=3,
                fact_predict_orders=2.0,
                fact_pay_for_order=150.0,
            ),
            5: PlanFactSummary(
                adv_id=5,
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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
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
        auto_shelf_bid_control_enabled=True
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
async def test_auto_adv_active_control_wb_wallet_fallback_when_bot_balance_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Нулевой баланс в БД бота, но положительный кошелёк WB — не пауза по insufficient_balance."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=50,
        search_status="started",
        auto_adv_id=20,
        search_adv_id=21,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    wb_balance = MagicMock()
    wb_balance.balance = 5000
    wb_balance.net = 0
    wb_balance.bonus = 0
    wb_balance.cashbacks = None

    wb_modifier = MagicMock()
    wb_modifier.get_campaign_balance = AsyncMock(return_value=wb_balance)
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(
        handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs
    ):
        for handler in handlers:
            await handler()
        return []

    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=20,
            fact_predict_orders=12.0,
            fact_pay_for_order=80.0,
        )
    )

    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(
        side_effect=_mock_load_time_settings_for_adv_ids
    )
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.pause_auto_campaign.assert_not_awaited()
    wb_modifier.pause_auction_campaign.assert_not_awaited()
    assert wb_modifier.get_campaign_balance.await_count == 1


@pytest.mark.asyncio
async def test_no_pause_when_plan_ranked_best_below_resolve_and_fact_above_resolve():
    """If plan_ranked best CPO <= resolve and fact CPO > resolve -> no pause."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=200,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    # plan_fact: fact_predict_orders valid, fact_pay_for_order > resolve
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=200, fact_predict_orders=12.0, fact_pay_for_order=383.87
        )
    )

    # view provider that returns best_cpo_bid_rub = 259.23 (below resolve 300)
    class ViewDTO:
        def __init__(self, best):
            self.best_cpo_bid_rub = best

    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=ViewDTO(259.23))
    # ensure build_selected_cpo_contract is awaitable and returns unavailable contract
    view_provider.build_selected_cpo_contract = AsyncMock(
        return_value=AutoShelfBidSelectedCpoContract(
            selected_bid_minor=None,
            selected_cpo_rub=None,
            updated_at=datetime.now(UTC),
            source="test",
            unavailable_reason="test_unavailable",
        )
    )

    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )

    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    async def _run_tasks_for_tests(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_pause_when_plan_ranked_best_above_resolve_and_fact_above_resolve():
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=201,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=201, fact_predict_orders=12.0, fact_pay_for_order=383.87
        )
    )
    class ViewDTO:
        def __init__(self, best):
            self.best_cpo_bid_rub = best
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=ViewDTO(350.0))
    view_provider.build_selected_cpo_contract = AsyncMock(
        return_value=AutoShelfBidSelectedCpoContract(
            selected_bid_minor=None,
            selected_cpo_rub=None,
            updated_at=datetime.now(UTC),
            source="test",
            unavailable_reason="test_unavailable",
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    # INC-AUTO-SHELF-PAUSE-01: shelf ON → MUST NOT mid-cycle cost pause.
    wb_modifier.pause_auto_campaign.assert_not_awaited()


async def _run_plan_ranked_best_unavailable_start_case(
    best_cpo_bid_rub: float | None,
) -> MagicMock:
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=0,
        search_status="pause",
        auto_adv_id=202,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=202, fact_predict_orders=12.0, fact_pay_for_order=383.87
        )
    )
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(
        return_value=type(
            "V",
            (),
            {
                "expected_enforced_bid_minor": None,
                "actual_bid_minor": None,
                "bid_sync_detail": "synced",
                "state_updated_at": datetime.now(UTC),
                "rec_bid_recommendation": {"plan_ranked": []},
                "best_cpo_bid_rub": best_cpo_bid_rub,
            },
        )()
    )
    view_provider.build_selected_cpo_contract = AsyncMock(
        return_value=AutoShelfBidSelectedCpoContract(
            selected_bid_minor=None,
            selected_cpo_rub=None,
            updated_at=datetime.now(UTC),
            source="test",
            unavailable_reason="test_unavailable",
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    return wb_modifier


@pytest.mark.asyncio
async def test_start_degraded_when_plan_ranked_best_missing_and_fact_above_resolve():
    wb_modifier = await _run_plan_ranked_best_unavailable_start_case(None)

    wb_modifier.start_auto_campaign.assert_awaited_once()
    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_degraded_when_plan_ranked_best_inf_and_fact_above_resolve():
    wb_modifier = await _run_plan_ranked_best_unavailable_start_case(float("inf"))

    wb_modifier.start_auto_campaign.assert_awaited_once()
    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_pause_degraded_when_plan_ranked_missing_and_fact_below_resolve():
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=203,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=203, fact_predict_orders=12.0, fact_pay_for_order=250.0
        )
    )
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(
        return_value=type(
            "V",
            (),
            {
                "expected_enforced_bid_minor": None,
                "actual_bid_minor": None,
                "bid_sync_detail": "synced",
                "state_updated_at": datetime.now(UTC),
                "rec_bid_recommendation": {"plan_ranked": []},
                "best_cpo_bid_rub": None,
            },
        )()
    )
    view_provider.build_selected_cpo_contract = AsyncMock(
        return_value=AutoShelfBidSelectedCpoContract(
            selected_bid_minor=None,
            selected_cpo_rub=None,
            updated_at=datetime.now(UTC),
            source="test",
            unavailable_reason="test_unavailable",
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_build_view_does_not_pause_by_fact_or_legacy_avg():
    """Missing bidder view must not stop an already started Auto shelf campaign."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=207,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=207, fact_predict_orders=12.0, fact_pay_for_order=383.87
        )
    )
    # Provider present but exposes no callable build_view/build_selected_cpo_contract.
    view_provider = MagicMock(spec=[])
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=200.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_build_view_no_pause_when_fact_below_resolve_despite_high_legacy_avg():
    """no_build_view degraded rule: fact <= resolve must not pause even if legacy avg > resolve."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=208,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=208, fact_predict_orders=12.0, fact_pay_for_order=250.0
        )
    )
    view_provider = MagicMock(spec=[])
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        # Legacy avg is HIGH (> resolve=300) -> old avg-based rule would have paused.
        new=AsyncMock(return_value=350.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_build_view_starts_by_fact_only_ignoring_high_legacy_avg():
    """no_build_view degraded resume rule: fact <= resolve allows start despite high legacy avg."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=0,
        search_status="pause",
        auto_adv_id=209,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=209, fact_predict_orders=12.0, fact_pay_for_order=250.0
        )
    )
    view_provider = MagicMock(spec=[])
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        # Legacy avg is HIGH (> resolve=300) -> old avg-based rule would have blocked start.
        new=AsyncMock(return_value=350.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.start_auto_campaign.assert_awaited_once()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_regression_legacy_avg_high_but_plan_ranked_low_no_pause():
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=204,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=204, fact_predict_orders=12.0, fact_pay_for_order=383.87
        )
    )
    # view best low
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=type("V", (), {"best_cpo_bid_rub": 259.23})())
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    # legacy avg high (but should be ignored for decision)
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=383.87),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_shelf_disabled_preserves_legacy_behavior():
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=205,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=False,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=205, fact_predict_orders=12.0, fact_pay_for_order=383.87
        )
    )
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock()
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=383.87),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.pause_auto_campaign.assert_awaited_once()
    view_provider.build_view.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_bad_fact_pay_for_order_no_pause():
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=206,
        plan_for_sales_for_day=10,
        target_price_for_order=300,
        max_price_for_order=400,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=206, fact_predict_orders=12.0, fact_pay_for_order=None
        )
    )
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=type("V", (), {"best_cpo_bid_rub": 350.0})())
    view_provider.build_selected_cpo_contract = AsyncMock(
        return_value=AutoShelfBidSelectedCpoContract(
            selected_bid_minor=None,
            selected_cpo_rub=None,
            updated_at=datetime.now(UTC),
            source="test",
            unavailable_reason="test_unavailable",
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.pause_auto_campaign.assert_not_awaited()



@pytest.mark.asyncio
async def test_wb_wallet_fallback_single_flight_when_handlers_run_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent auto + search handlers for one adv must not duplicate get_campaign_balance."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=50,
        search_status="started",
        auto_adv_id=30,
        search_adv_id=31,
    )
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    wb_balance = MagicMock()
    wb_balance.balance = 1000
    wb_balance.net = 0
    wb_balance.bonus = 0
    wb_balance.cashbacks = None

    wb_modifier = MagicMock()
    wb_modifier.get_campaign_balance = AsyncMock(return_value=wb_balance)
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(
        handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs
    ):
        await asyncio.gather(*(h() for h in handlers))
        return []

    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(
        side_effect=_mock_load_time_settings_for_adv_ids
    )
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    assert wb_modifier.get_campaign_balance.await_count == 1


@pytest.mark.asyncio
async def test_auto_adv_active_control_wb_wallet_fallback_cashbacks_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WB отдаёт 0 в balance/net/bonus, но есть cashback — fallback считает кошелёк положительным."""
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=50,
        search_status="started",
        auto_adv_id=22,
        search_adv_id=23,
    )
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    cb_item = MagicMock()
    cb_item.sum_ = 3000
    cb_item.percent = 50
    cb_item.expiration_date = None
    wb_balance = MagicMock()
    wb_balance.balance = 0
    wb_balance.net = 0
    wb_balance.bonus = 0
    wb_balance.cashbacks = [cb_item]

    wb_modifier = MagicMock()
    wb_modifier.get_campaign_balance = AsyncMock(return_value=wb_balance)
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    async def mock_run_tasks(
        handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs
    ):
        for handler in handlers:
            await handler()
        return []

    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(
        side_effect=_mock_load_time_settings_for_adv_ids
    )
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=mock_run_tasks,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.pause_auto_campaign.assert_not_awaited()
    wb_modifier.pause_auction_campaign.assert_not_awaited()


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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_shelf_bid_control_pauses_when_avg_cost_and_total_cpo_are_high():
    """LEGACY_BASELINE note → FINAL_ACCEPTANCE: shelf ON MUST NOT mid-cycle cost pause.

    Tasks §1.1/1.12: earlier characterization paused Auto with COST_RULE_FAILED;
    INC-AUTO-SHELF-PAUSE-01 kills that branch while module ON.
    """
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=120.0,
        auto_shelf_bid_control_enabled=True,
    )

    wb_modifier.pause_auto_campaign.assert_not_awaited()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_shelf_bid_control_does_not_pause_when_total_cpo_is_ok():
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=100.0,
        auto_shelf_bid_control_enabled=True,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()
    # Shelf ON + started: ordinary cost no-op → may re-assert BUDGET_OK_COST_OK.
    if wb_modifier.reason_manager.set.await_count:
        _adv_id, campaign_type, reason = wb_modifier.reason_manager.set.await_args.args
        assert campaign_type == "auto"
        assert reason.reason_code == AutoReasonCode.BUDGET_OK_COST_OK


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fact_pay_for_order",
    [None, "bad", float("nan"), float("inf")],
)
async def test_auto_adv_shelf_bid_control_does_not_pause_when_total_cpo_missing_or_bad(
    fact_pay_for_order: object,
):
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=fact_pay_for_order,
        fact_predict_orders=12.0,
        auto_shelf_bid_control_enabled=True,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_shelf_bid_control_starts_when_avg_cost_is_ok():
    wb_modifier = await _run_auto_cost_rule_case(
        auto_status="pause",
        avg_cost=100.0,
        fact_pay_for_order=None,
        auto_shelf_bid_control_enabled=True,
    )

    wb_modifier.start_auto_campaign.assert_awaited_once()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_shelf_bid_control_prefers_selected_cpo_over_legacy():
    selected_contract = AutoShelfBidSelectedCpoContract(
        selected_bid_minor=12300,
        selected_cpo_rub=90.0,
        updated_at=datetime.now(UTC),
        source="rec_bid_recommendation.plan_ranked[selected_bid_minor=12300]",
    )
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=120.0,
        auto_shelf_bid_control_enabled=True,
        selected_cpo_contract=selected_contract,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.selected_cpo_provider.build_view.assert_awaited_once_with(
        1001
    )
    wb_modifier.selected_cpo_provider.build_selected_cpo_contract.assert_not_awaited()
    wb_modifier.legacy_avg_cost_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_adv_shelf_bid_control_does_not_pause_when_selected_cpo_missing():
    unavailable_contract = AutoShelfBidSelectedCpoContract(
        selected_bid_minor=12300,
        selected_cpo_rub=None,
        updated_at=datetime.now(UTC),
        source="rec_bid_recommendation.plan_ranked[selected_bid_minor=12300]",
        unavailable_reason="selected_bid_not_synced",
    )
    # Build service manually to control view provider behavior.
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=301,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(adv_id=301, fact_predict_orders=12.0, fact_pay_for_order=120.0)
    )
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(
        return_value=type(
            "V",
            (),
            {
                "enabled": True,
                "expected_enforced_bid_minor": None,
                "actual_bid_minor": None,
                "bid_sync_detail": "synced",
                "state_updated_at": datetime.now(UTC),
                "rec_bid_recommendation": {"plan_ranked": []},
                "best_cpo_bid_rub": None,
            },
        )()
    )
    view_provider.build_selected_cpo_contract = AsyncMock(return_value=unavailable_contract)
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_shelf_watchdog_builds_view_once_per_pass():
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=401,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )

    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=401,
            fact_predict_orders=12.0,
            fact_pay_for_order=90.0,
        )
    )

    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(
        return_value=SimpleNamespace(
            enabled=True,
            expected_enforced_bid_minor=12300,
            actual_bid_minor=12300,
            bid_sync_detail="synced",
            state_updated_at=datetime.now(UTC),
            rec_bid_recommendation={
                "plan_ranked": [{"bid": 12300, "cpo_rub": 90.0}]
            },
            best_cpo_bid_rub=90.0,
        )
    )
    view_provider.build_selected_cpo_contract = AsyncMock()

    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    view_provider.build_view.assert_awaited_once_with(401)
    view_provider.build_selected_cpo_contract.assert_not_awaited()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_shelf_bid_control_pauses_when_selected_cpo_and_total_are_high():
    selected_contract = AutoShelfBidSelectedCpoContract(
        selected_bid_minor=12300,
        selected_cpo_rub=150.0,
        updated_at=datetime.now(UTC),
        source="rec_bid_recommendation.plan_ranked[selected_bid_minor=12300]",
    )
    # Build service manually with view_provider returning best equal to selected
    adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="started",
        search_limit=0,
        search_status="pause",
        auto_adv_id=302,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    wb_modifier = MagicMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(adv_id=302, fact_predict_orders=12.0, fact_pay_for_order=120.0)
    )
    view_provider = MagicMock()
    # ensure build_view returns best equal to selected_contract.selected_cpo_rub
    view_provider.build_view = AsyncMock(return_value=type("V", (), {"best_cpo_bid_rub": 150.0})())
    view_provider.build_selected_cpo_contract = AsyncMock(return_value=selected_contract)
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
        auto_shelf_bid_control_view_provider=view_provider,
    )
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings_for_adv_ids)
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks_for_tests), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=90.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])
    # INC-AUTO-SHELF-PAUSE-01: shelf ON → mid-cycle cost pause Forbidden.
    wb_modifier.pause_auto_campaign.assert_not_awaited()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_pause_when_total_cpo_is_ok():
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=100.0,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_pause_when_avg_cost_is_ok():
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=100.0,
        fact_pay_for_order=150.0,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_starts_when_avg_cost_ok_without_total_cpo():
    wb_modifier = await _run_auto_cost_rule_case(
        auto_status="pause",
        avg_cost=100.0,
        fact_pay_for_order=None,
    )

    wb_modifier.start_auto_campaign.assert_awaited_once()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_pause_when_avg_cost_ok_without_total_cpo():
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=100.0,
        fact_pay_for_order=None,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_starts_when_avg_cost_ok_and_total_cpo_high():
    wb_modifier = await _run_auto_cost_rule_case(
        auto_status="pause",
        avg_cost=100.0,
        fact_pay_for_order=150.0,
    )

    wb_modifier.start_auto_campaign.assert_awaited_once()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_pauses_when_avg_cost_and_total_cpo_are_high():
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=120.0,
    )

    wb_modifier.pause_auto_campaign.assert_awaited_once()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_pause_on_equal_values():
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=100.0,
        fact_pay_for_order=100.0,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("resolved_target_cost", "avg_cost", "fact_pay_for_order"),
    [
        (None, 150.0, 120.0),
        (100.0, None, 120.0),
        (100.0, 150.0, None),
        (float("nan"), 150.0, 120.0),
        (100.0, float("nan"), 120.0),
        (100.0, 150.0, float("nan")),
        ("bad", 150.0, 120.0),
        (100.0, "bad", 120.0),
        (100.0, 150.0, "bad"),
    ],
)
async def test_auto_adv_cost_rule_does_not_pause_on_missing_or_bad_values(
    resolved_target_cost: object,
    avg_cost: object,
    fact_pay_for_order: object,
):
    wb_modifier = await _run_auto_cost_rule_case(
        resolved_target_cost=resolved_target_cost,
        avg_cost=avg_cost,
        fact_pay_for_order=fact_pay_for_order,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_pause_without_fact_predict_orders():
    wb_modifier = await _run_auto_cost_rule_case(
        fact_predict_orders=None,
        avg_cost=150.0,
        fact_pay_for_order=120.0,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_start_without_fact_predict_orders():
    wb_modifier = await _run_auto_cost_rule_case(
        auto_status="pause",
        fact_predict_orders=None,
        avg_cost=150.0,
        fact_pay_for_order=120.0,
    )

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("fact_predict_orders", ["bad", float("nan")])
async def test_auto_adv_cost_rule_does_not_pause_on_bad_fact_predict_orders(
    fact_predict_orders: object,
):
    wb_modifier = await _run_auto_cost_rule_case(
        fact_predict_orders=fact_predict_orders,
        avg_cost=150.0,
        fact_pay_for_order=120.0,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_start_when_avg_cost_high_but_total_cpo_ok():
    wb_modifier = await _run_auto_cost_rule_case(
        auto_status="pause",
        avg_cost=150.0,
        fact_pay_for_order=100.0,
    )

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_start_when_avg_cost_high_without_total_cpo():
    wb_modifier = await _run_auto_cost_rule_case(
        auto_status="pause",
        avg_cost=150.0,
        fact_pay_for_order=None,
    )

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_does_not_pause_when_avg_cost_high_without_total_cpo():
    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=None,
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.start_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_cost_rule_blocks_start_when_avg_cost_and_total_cpo_are_high():
    wb_modifier = await _run_auto_cost_rule_case(
        auto_status="pause",
        avg_cost=150.0,
        fact_pay_for_order=120.0,
    )

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.pause_auto_campaign.assert_not_called()


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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.start_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_does_not_start_when_avg_cost_above_target():
    """Separate budget: PAUSE, budget OK, but both CPO values exceed target -> start not called."""
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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.pause_auto_campaign.assert_not_called()


@pytest.mark.asyncio
async def test_auto_adv_common_budget_does_not_start_auto_when_avg_cost_high_but_total_cpo_ok():
    """Common budget: PAUSE, budget OK, avg_cost high but total CPO OK -> auto blocked."""
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
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
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


# ---------------------------------------------------------------------------
# Абсолютный (lifetime) лимит расхода РК
# ---------------------------------------------------------------------------


def _total_limit_service() -> tuple[AutoAdvActiveControlService, MagicMock]:
    """Сервис с замоканным WBModifier для проверок абсолютного лимита."""
    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
    )
    return service, wb_modifier


async def _run_with_total_spend(
    service: AutoAdvActiveControlService,
    adv: _FakeComplexAdv,
    *,
    daily_spend: float,
    total_spend_by_adv: dict[int, float] | Exception,
) -> tuple[AsyncMock, AsyncMock]:
    """Прогнать ensure_campaigns_active с подменой суточного и all-time расхода.

    Returns:
        Моки ``_set_auto_reason`` и ``_set_search_reason`` для проверки причин.
    """

    async def mock_daily_spend(*args, **kwargs) -> float:
        return daily_spend

    async def mock_total_spend(adv_ids: list[int]) -> float:
        if isinstance(total_spend_by_adv, Exception):
            raise total_spend_by_adv
        return sum(total_spend_by_adv.get(adv_id, 0.0) for adv_id in adv_ids)

    auto_reason_mock = AsyncMock()
    search_reason_mock = AsyncMock()
    mock_ts_repo = MagicMock()
    mock_ts_repo.load_for_adv_ids = AsyncMock(
        side_effect=_mock_load_time_settings_for_adv_ids
    )
    with patch(
        f"{_SERVICE_MODULE}.run_tasks",
        new=_run_tasks_for_tests,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(side_effect=mock_daily_spend),
    ), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_total_spend_by_advs",
        new=AsyncMock(side_effect=mock_total_spend),
    ), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._set_auto_reason",
        new=auto_reason_mock,
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._set_search_reason",
        new=search_reason_mock,
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts_repo):
        await service.ensure_campaigns_active([adv])

    return auto_reason_mock, search_reason_mock


@pytest.mark.asyncio
async def test_total_limit_pauses_both_legs_in_separate_mode():
    """Раздельный режим: каждая нога паузится по своему абсолютному лимиту."""
    adv = _FakeComplexAdv(
        auto_limit=100_000,
        auto_status="started",
        search_limit=100_000,
        search_status="started",
        auto_adv_id=21,
        search_adv_id=22,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        daily_spend=10.0,
        total_spend_by_adv={21: 600.0, 22: 700.0},
    )

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.start_auction_campaign.assert_not_called()
    assert auto_reason.await_args[0][2] == AutoReasonCode.AUTO_TOTAL_EXCEEDED
    assert search_reason.await_args[0][2] == AuctionReasonCode.SEARCH_TOTAL_EXCEEDED


@pytest.mark.asyncio
async def test_total_limit_pauses_both_legs_in_common_mode():
    """Общий бюджет: паузим обе ноги по сумме all-time расхода."""
    adv = _FakeComplexAdv(
        auto_limit=0,
        auto_status="started",
        search_limit=0,
        search_status="started",
        auto_adv_id=31,
        search_adv_id=32,
        use_common_budget=True,
        common_budget_daily_limit=100_000,
        common_budget_total_limit=500,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        daily_spend=10.0,
        # 300 + 300 = 600 >= 500, хотя по отдельности каждая нога под лимитом
        total_spend_by_adv={31: 300.0, 32: 300.0},
    )

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv)
    assert auto_reason.await_args[0][2] == AutoReasonCode.COMMON_TOTAL_EXCEEDED
    assert search_reason.await_args[0][2] == AuctionReasonCode.COMMON_TOTAL_EXCEEDED


@pytest.mark.asyncio
async def test_total_limit_zero_does_not_pause():
    """Лимит 0 = выключено: абсолютный гейт не трогает кампании."""
    adv = _FakeComplexAdv(
        auto_limit=100_000,
        auto_status="started",
        search_limit=100_000,
        search_status="started",
        auto_adv_id=41,
        search_adv_id=42,
        auto_budget_total_limit=0,
        search_auto_budget_total_limit=0,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        daily_spend=10.0,
        total_spend_by_adv={41: 1_000_000.0, 42: 1_000_000.0},
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.pause_auction_campaign.assert_not_called()
    auto_codes = [call.args[2] for call in auto_reason.await_args_list]
    search_codes = [call.args[2] for call in search_reason.await_args_list]
    assert AutoReasonCode.AUTO_TOTAL_EXCEEDED not in auto_codes
    assert AuctionReasonCode.SEARCH_TOTAL_EXCEEDED not in search_codes


@pytest.mark.asyncio
async def test_total_limit_takes_precedence_over_daily_limit():
    """Абсолютный лимит терминален: причина перекрывает суточный гейт."""
    adv = _FakeComplexAdv(
        auto_limit=1,
        auto_status="started",
        search_limit=1,
        search_status="started",
        auto_adv_id=51,
        search_adv_id=52,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        # суточный лимит тоже исчерпан, но абсолютный проверяется раньше
        daily_spend=5_000.0,
        total_spend_by_adv={51: 600.0, 52: 600.0},
    )

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv)
    assert auto_reason.await_args[0][2] == AutoReasonCode.AUTO_TOTAL_EXCEEDED
    assert search_reason.await_args[0][2] == AuctionReasonCode.SEARCH_TOTAL_EXCEEDED


@pytest.mark.asyncio
async def test_total_limit_pauses_when_spend_unknown_in_separate_mode():
    """Ошибка ClickHouse при заданном лимите — fail-closed пауза, не пропуск гейта."""
    adv = _FakeComplexAdv(
        auto_limit=100_000,
        auto_status="started",
        search_limit=100_000,
        search_status="started",
        auto_adv_id=61,
        search_adv_id=62,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        daily_spend=10.0,
        total_spend_by_adv=RuntimeError("clickhouse down"),
    )

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv)
    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.start_auction_campaign.assert_not_called()
    assert auto_reason.await_args[0][2] == AutoReasonCode.AUTO_TOTAL_UNKNOWN
    assert search_reason.await_args[0][2] == AuctionReasonCode.SEARCH_TOTAL_UNKNOWN


@pytest.mark.asyncio
async def test_total_limit_pauses_when_spend_unknown_in_common_mode():
    """Общий режим: недоступная статистика тоже держит обе ноги на паузе."""
    adv = _FakeComplexAdv(
        auto_limit=0,
        auto_status="started",
        search_limit=0,
        search_status="started",
        auto_adv_id=71,
        search_adv_id=72,
        use_common_budget=True,
        common_budget_daily_limit=100_000,
        common_budget_total_limit=500,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        daily_spend=10.0,
        total_spend_by_adv=RuntimeError("clickhouse down"),
    )

    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv)
    assert auto_reason.await_args[0][2] == AutoReasonCode.COMMON_TOTAL_UNKNOWN
    assert search_reason.await_args[0][2] == AuctionReasonCode.COMMON_TOTAL_UNKNOWN


@pytest.mark.asyncio
async def test_total_limit_spend_unknown_does_not_restart_paused_campaign():
    """Регресс: РК на паузе не должна перезапуститься при сбое ClickHouse.

    Суточный лимит и себестоимость в норме, статус ``PAUSE`` — без fail-closed
    гейта обычная ветка старта снова запустила бы уже остановленную кампанию.
    """
    adv = _FakeComplexAdv(
        auto_limit=100_000,
        auto_status="pause",
        search_limit=100_000,
        search_status="pause",
        auto_adv_id=81,
        search_adv_id=82,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        daily_spend=10.0,
        total_spend_by_adv=RuntimeError("clickhouse down"),
    )

    wb_modifier.start_auto_campaign.assert_not_called()
    wb_modifier.start_auction_campaign.assert_not_called()
    # Кампании уже на паузе — повторный WB-вызов не нужен, но причина пишется.
    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.pause_auction_campaign.assert_not_called()
    assert auto_reason.await_args[0][2] == AutoReasonCode.AUTO_TOTAL_UNKNOWN
    assert search_reason.await_args[0][2] == AuctionReasonCode.SEARCH_TOTAL_UNKNOWN


@pytest.mark.asyncio
async def test_total_limit_zero_ignores_clickhouse_error():
    """Лимит выключен: сбой статистики не влияет на активность РК."""
    adv = _FakeComplexAdv(
        auto_limit=100_000,
        auto_status="started",
        search_limit=100_000,
        search_status="started",
        auto_adv_id=91,
        search_adv_id=92,
        auto_budget_total_limit=0,
        search_auto_budget_total_limit=0,
    )
    service, wb_modifier = _total_limit_service()

    auto_reason, search_reason = await _run_with_total_spend(
        service,
        adv,
        daily_spend=10.0,
        total_spend_by_adv=RuntimeError("clickhouse down"),
    )

    wb_modifier.pause_auto_campaign.assert_not_called()
    wb_modifier.pause_auction_campaign.assert_not_called()
    auto_codes = [call.args[2] for call in auto_reason.await_args_list]
    search_codes = [call.args[2] for call in search_reason.await_args_list]
    assert AutoReasonCode.AUTO_TOTAL_UNKNOWN not in auto_codes
    assert AuctionReasonCode.SEARCH_TOTAL_UNKNOWN not in search_codes
