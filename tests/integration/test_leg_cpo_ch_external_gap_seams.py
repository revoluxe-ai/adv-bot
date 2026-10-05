"""Integration: leg-CPO CH external-call seams (change separate-auto-search-cpo).

Каждый тест вызывает production CH read-path через ``patch_get_clickhouse_client``,
Arrange seed в ``test_adv_bot_clickhouse.full_adv_wb_stat`` и re-read persisted rows.
Live pytest намеренно не запускается в рамках ``/opsx-close-external-gap`` без
``AUTHORIZE_ONE_LIVE_RUN``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from clickhouse_connect import get_async_client
from fakeredis import FakeRedis
from sqlalchemy.ext.asyncio import AsyncSession

import app.modules.common_advs_stat.data_manager as common_advs_stat_module
import app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service as auto_shelf_telegram_module
import app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider as auto_shelf_view_module
import app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat as full_wb_adv_stat_module
from app.client_bot.user_interface.services import keyword_v3_profile_loader
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.adv_setting_menu import (
    AdvSettingMenu,
)
from app.modules.common_advs_stat.data_manager import CommonAdvsStatDataManager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    MainBidRefreshResult,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service import (
    AutoShelfBidControlTelegramService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    OptimizationMetric,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    UpdateClusterBidsManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.wb_stat_manager.leg_cpo import (
    load_leg_cpo_snapshot,
    load_leg_cpo_snapshots,
)
from tests.support.leg_cpo_ch_seed import (
    LEG_CPO_AUTO_ADV_ID,
    LEG_CPO_FIXED_DAYS,
    LEG_CPO_FIXED_NOW,
    LEG_CPO_SEARCH_ADV_ID,
    reread_leg_spend_totals,
    seed_leg_cpo_pair_rows,
    truncate_full_adv_wb_stat,
)
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


def _patch_leg_cpo_ch(
    monkeypatch: pytest.MonkeyPatch,
    clickhouse_client: get_async_client,
) -> None:
    """Redirect production ``get_clickhouse_client`` to Guarded test CH."""
    patch_get_clickhouse_client(
        monkeypatch,
        [full_wb_adv_stat_module],
        clickhouse_client,
    )


def _auto_adv_setting(
    *,
    adv_id: int = LEG_CPO_AUTO_ADV_ID,
    search_adv_id: int | None = LEG_CPO_SEARCH_ADV_ID,
    wb_cabinet_id: int = 1,
) -> AdvSetting:
    """Минимальный AdvSetting для leg-CPO integration seams."""
    return AdvSetting(
        adv_id=adv_id,
        name="leg-cpo-gap",
        wb_cabinet_id=wb_cabinet_id,
        active_status="started",
        bot_active=True,
        nmids=[12345],
        search_adv_id=search_adv_id,
        cpm=100,
        plan_for_sales_for_day=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        orders_source_for_auto_mode=OrdersSourceForAutoMode.ADV_SUM,
        sales_predict_method=FactMethods.DIRECT_SALES,
    )


@pytest.mark.integration
async def test_load_leg_cpo_snapshot_reads_live_clickhouse(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``load_leg_cpo_snapshot`` проходит через live CH wrapper, не только callee SQL."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    start_date, end_date = await seed_leg_cpo_pair_rows(clickhouse_client)
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    snapshot = await load_leg_cpo_snapshot(
        auto_adv_id=LEG_CPO_AUTO_ADV_ID,
        search_adv_id=LEG_CPO_SEARCH_ADV_ID,
        now=LEG_CPO_FIXED_NOW,
        days=LEG_CPO_FIXED_DAYS,
    )

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID, LEG_CPO_SEARCH_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted[LEG_CPO_AUTO_ADV_ID][0] == pytest.approx(600.0)
    assert persisted[LEG_CPO_SEARCH_ADV_ID][0] == pytest.approx(300.0)
    assert snapshot.auto_cpo == pytest.approx(600.0 / 2)
    assert snapshot.search_cpo == pytest.approx(300.0 / 3)
    assert snapshot.start_date == start_date
    assert snapshot.end_date == end_date


@pytest.mark.integration
async def test_load_leg_cpo_snapshots_batch_reads_live_clickhouse(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch loader ``load_leg_cpo_snapshots`` делает один CH-read без N+1 mock."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    start_date, end_date = await seed_leg_cpo_pair_rows(clickhouse_client)
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    auto_setting = _auto_adv_setting()
    complex_adv = ComplexAdv(adv_setting=auto_setting)
    snapshots = await load_leg_cpo_snapshots(
        [complex_adv],
        now=LEG_CPO_FIXED_NOW,
        days=LEG_CPO_FIXED_DAYS,
    )

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID, LEG_CPO_SEARCH_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted
    snapshot = snapshots[LEG_CPO_AUTO_ADV_ID]
    assert snapshot.auto_cpo == pytest.approx(600.0 / 2)
    assert snapshot.search_cpo == pytest.approx(300.0 / 3)
    assert snapshot.end_date == end_date


@pytest.mark.integration
async def test_common_advs_stat_get_data_leg_cpo_from_live_clickhouse(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``CommonAdvsStatDataManager.get_data`` читает leg CPO через live CH producer."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    now = datetime.now()
    await seed_leg_cpo_pair_rows(
        clickhouse_client,
        now=now,
        days=LEG_CPO_FIXED_DAYS,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    adv = MagicMock()
    adv.adv_id = LEG_CPO_AUTO_ADV_ID
    adv.search_adv_id = LEG_CPO_SEARCH_ADV_ID
    adv.nmids = [12345]
    adv.orders_source_for_auto_mode = OrdersSourceForAutoMode.ADV_SUM
    adv.hard_min_ctr = None
    adv.cpm = 100
    adv.sales_predict_method = FactMethods.DIRECT_SALES

    manager = CommonAdvsStatDataManager()
    manager._fetch_auction_cpm_if_any = AsyncMock(return_value=90)  # type: ignore[method-assign]
    manager._get_predict_orders_for_day = AsyncMock(return_value=2.0)  # type: ignore[method-assign]
    monkeypatch.setattr(
        common_advs_stat_module.common_stat_manager,
        "get_stats_for_last_period",
        AsyncMock(return_value=MagicMock(orders=2, add_to_cart=1)),
    )
    monkeypatch.setattr(
        common_advs_stat_module.full_wb_adv_stat,
        "get_keywords_spend",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        common_advs_stat_module.full_wb_adv_stat,
        "get_additional_cost_per_order_for_adv",
        AsyncMock(return_value=None),
    )

    result = await manager.get_data(adv, [], last_days=LEG_CPO_FIXED_DAYS)

    start_date, end_date = now - timedelta(days=LEG_CPO_FIXED_DAYS - 1), now
    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID, LEG_CPO_SEARCH_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted[LEG_CPO_AUTO_ADV_ID][0] == pytest.approx(600.0)
    assert result.auto_cpo == pytest.approx(600.0 / 2)
    assert result.search_cpo == pytest.approx(300.0 / 3)


@pytest.mark.integration
async def test_wb_shop_data_manager_attach_leg_cpo_reads_live_clickhouse(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``WBShopDataManager.attach_leg_cpo`` batch-read через live CH, не AsyncMock."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    runtime_now = datetime.now()
    start_date, end_date = await seed_leg_cpo_pair_rows(
        clickhouse_client,
        now=runtime_now,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    cabinet = WBCabinet(
        shop_id=f"leg_cpo_attach_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    manager = WBShopDataManager(
        wb_cabinet=cabinet,
        tasks_manager=None,
        wb_api_data_manager=MagicMock(),
        wb_manager=None,
    )
    complex_adv = ComplexAdv(adv_setting=_auto_adv_setting())

    await manager.attach_leg_cpo([complex_adv])

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID, LEG_CPO_SEARCH_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted
    assert complex_adv.auto_fact_cpo == pytest.approx(600.0 / 2)
    assert complex_adv.search_fact_cpo == pytest.approx(300.0 / 3)
    assert complex_adv.leg_cpo_snapshot is not None
    assert complex_adv.leg_cpo_snapshot.end_date == end_date


@pytest.mark.integration
async def test_keyword_v3_build_complex_adv_attaches_live_leg_cpo(
    async_session: AsyncSession,
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``keyword_v3_profile_loader._build_complex_adv`` вызывает live leg-CPO loader."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    runtime_now = datetime.now()
    start_date, end_date = await seed_leg_cpo_pair_rows(
        clickhouse_client,
        now=runtime_now,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    cabinet = WBCabinet(
        shop_id=f"kw_v3_leg_cpo_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(cabinet)
    await async_session.flush()

    search_adv = AdvSetting(
        adv_id=LEG_CPO_SEARCH_ADV_ID,
        name="search-leg",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        nmids=[12345],
        cpm=90,
    )
    auto_adv = _auto_adv_setting(
        wb_cabinet_id=cabinet.id,
        search_adv_id=LEG_CPO_SEARCH_ADV_ID,
    )
    async_session.add(search_adv)
    async_session.add(auto_adv)
    await async_session.flush()

    complex_adv = await keyword_v3_profile_loader._build_complex_adv(  # noqa: SLF001
        auto_adv,
        cabinet.shop_id,
    )

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID, LEG_CPO_SEARCH_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted
    assert complex_adv.auto_fact_cpo == pytest.approx(600.0 / 2)
    assert complex_adv.search_fact_cpo == pytest.approx(300.0 / 3)


@pytest.mark.integration
async def test_adv_setting_menu_resolve_cost_activity_attaches_live_leg_cpo(
    async_session: AsyncSession,
    clickhouse_client: get_async_client,
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``AdvSettingMenu._resolve_cost_activity_complex_adv`` читает leg CPO из live CH."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    runtime_now = datetime.now()
    start_date, end_date = await seed_leg_cpo_pair_rows(
        clickhouse_client,
        now=runtime_now,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    cabinet = WBCabinet(
        shop_id=f"menu_leg_cpo_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(cabinet)
    await async_session.flush()

    search_adv = AdvSetting(
        adv_id=LEG_CPO_SEARCH_ADV_ID,
        name="search-leg-menu",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        nmids=[12345],
        cpm=90,
    )
    auto_adv = _auto_adv_setting(
        wb_cabinet_id=cabinet.id,
        search_adv_id=LEG_CPO_SEARCH_ADV_ID,
    )
    async_session.add(search_adv)
    async_session.add(auto_adv)
    await async_session.flush()

    menu = object.__new__(AdvSettingMenu)
    menu.adv = auto_adv
    menu._redis_client = fake_redis

    complex_adv = await menu._resolve_cost_activity_complex_adv()  # noqa: SLF001

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID, LEG_CPO_SEARCH_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted
    assert complex_adv.auto_fact_cpo == pytest.approx(600.0 / 2)
    assert complex_adv.search_fact_cpo == pytest.approx(300.0 / 3)


@pytest.mark.integration
async def test_auto_shelf_view_provider_build_view_uses_live_auto_leg_cpo(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``AutoShelfBidControlViewProvider.build_view`` не патчит ``load_leg_cpo_snapshot``."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    runtime_now = datetime.now()
    start_date, end_date = await seed_leg_cpo_pair_rows(
        clickhouse_client,
        auto_adv_id=LEG_CPO_AUTO_ADV_ID,
        search_adv_id=None,
        now=runtime_now,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = LEG_CPO_AUTO_ADV_ID
    adv.search_adv_id = None
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = None
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 999.0
    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        auto_shelf_view_module,
        "PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted[LEG_CPO_AUTO_ADV_ID][0] == pytest.approx(600.0)
    assert view.fact_cpo == pytest.approx(600.0 / 2)
    assert view.optimization_metric == OptimizationMetric.CTR


@pytest.mark.integration
async def test_auto_shelf_telegram_build_view_delegates_live_leg_cpo(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``AutoShelfBidControlTelegramService.build_view`` достигает live leg-CPO через provider."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    runtime_now = datetime.now()
    start_date, end_date = await seed_leg_cpo_pair_rows(
        clickhouse_client,
        auto_adv_id=LEG_CPO_AUTO_ADV_ID,
        search_adv_id=None,
        now=runtime_now,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = LEG_CPO_AUTO_ADV_ID
    adv.search_adv_id = None
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = None
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    view_provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(
            get_bid_stats=AsyncMock(return_value=[]),
            get_best_bid_by_ctr=AsyncMock(return_value=None),
            get_best_bid_by_cart_cpa=AsyncMock(return_value=None),
        ),
    )
    view_provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    view_provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 999.0
    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        auto_shelf_view_module,
        "PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    telegram_service = AutoShelfBidControlTelegramService(
        redis_client=MagicMock(),
        repository=repository,
        view_provider=view_provider,
    )

    view = await telegram_service.build_view(adv_setting_original_id=1)

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted
    assert view.fact_cpo == pytest.approx(600.0 / 2)


@pytest.mark.integration
async def test_auto_shelf_telegram_apply_main_bid_refresh_reads_live_leg_cpo(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``apply_main_bid_refresh_if_needed`` читает leg CPO из live CH, не stub loader."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    runtime_now = datetime.now()
    start_date, end_date = await seed_leg_cpo_pair_rows(
        clickhouse_client,
        auto_adv_id=LEG_CPO_AUTO_ADV_ID,
        search_adv_id=None,
        now=runtime_now,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = LEG_CPO_AUTO_ADV_ID
    adv.search_adv_id = None
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = None
    adv.bot_active = True
    adv.auto_adv_active_status = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    main_state = SimpleNamespace(current_mode="main", current_main_bid_minor=450)
    settings_obj = MagicMock()
    settings_obj.max_bid_minor = 500
    settings_obj.currency = "RUB"

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=main_state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    view_provider = MagicMock()
    view_provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)
    view_provider._analytics = MagicMock()

    captured_auto_fact_cpo: list[float | None] = []

    async def _capture_build_snapshot(complex_adv: object, **_: object) -> SimpleNamespace:
        captured_auto_fact_cpo.append(getattr(complex_adv, "auto_fact_cpo", None))
        return SimpleNamespace()

    manager_instance = MagicMock()
    manager_instance.build_decision_snapshot = AsyncMock(
        side_effect=_capture_build_snapshot
    )

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_pay_for_order = 999.0
    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)

    telegram_service = AutoShelfBidControlTelegramService(
        redis_client=MagicMock(),
        repository=repository,
        view_provider=view_provider,
    )
    telegram_service._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]

    with (
        patch.object(
            auto_shelf_telegram_module,
            "AutoShelfBidControlManager",
            return_value=manager_instance,
        ),
        patch.object(
            auto_shelf_telegram_module,
            "PlanFactReader",
            return_value=mock_plan_fact_reader,
        ),
    ):
        result = await telegram_service.apply_main_bid_refresh_if_needed(1)

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted[LEG_CPO_AUTO_ADV_ID][0] == pytest.approx(600.0)
    assert result == MainBidRefreshResult.NO_CHANGE
    assert len(captured_auto_fact_cpo) == 1
    assert captured_auto_fact_cpo[0] == pytest.approx(600.0 / 2)
    manager_instance.build_decision_snapshot.assert_awaited_once()


@pytest.mark.integration
async def test_update_cluster_bids_get_fact_datas_search_cpo_from_live_ch(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``UpdateClusterBidsManager._get_fact_datas`` берёт Search CPO из live batch loader."""
    await truncate_full_adv_wb_stat(clickhouse_client)
    runtime_now = datetime.now()
    start_date, end_date = await seed_leg_cpo_pair_rows(
        clickhouse_client,
        now=runtime_now,
    )
    _patch_leg_cpo_ch(monkeypatch, clickhouse_client)

    plan_fact_reader = MagicMock()
    plan_fact_reader.get_latest_plan_facts = AsyncMock(
        return_value={LEG_CPO_AUTO_ADV_ID: SimpleNamespace()}
    )
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
    )
    adv_setting = _auto_adv_setting()
    complex_adv = ComplexAdv(adv_setting=adv_setting)
    aggregate_fact = FactData(
        predict_orders=2.0,
        original_orders=2.0,
        pay_for_order=999.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    monkeypatch.setattr(
        "app.modules.plan_fact.provider.PlanFactProvider.fact_data_from_plan_fact_summary",
        lambda *_args, **_kwargs: aggregate_fact,
    )

    result = await manager._get_fact_datas([complex_adv])  # noqa: SLF001

    persisted = await reread_leg_spend_totals(
        clickhouse_client,
        [LEG_CPO_AUTO_ADV_ID, LEG_CPO_SEARCH_ADV_ID],
        start_date=start_date,
        end_date=end_date,
    )
    assert persisted[LEG_CPO_SEARCH_ADV_ID][0] == pytest.approx(300.0)
    assert result[LEG_CPO_AUTO_ADV_ID].pay_for_order == pytest.approx(300.0 / 3)
