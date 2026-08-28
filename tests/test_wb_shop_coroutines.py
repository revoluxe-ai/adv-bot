from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessState,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
import app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager as calculated_keywords_manager_module
from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
    CalculatedKeywordsManager,
)
from app.utils.redis_cache import setup_redis_cache
from tests.factories.clickhouse_factory import (
    CLUSTERS_ADV_STATS_COLUMNS,
    ClustersAdvStatsFactory,
    build_clusters_adv_stats_rows,
)
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client


@pytest.fixture
def client_session_mock():
    session = AsyncMock()
    session.close = MagicMock()
    return session


def _search_adv_started() -> MagicMock:
    search = MagicMock(spec=AdvSetting)
    search.adv_id = 90001
    search.active_status = "started"
    return search


@pytest.mark.parametrize(
    "fact_method",
    [
        FactMethods.DIRECT_SALES,
        FactMethods.BY_CARTS,
    ],
)
@pytest.mark.asyncio
async def test_adv_settings_auto_update(
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fact_method,
    fake_redis,
    monkeypatch,
):
    """v3-only: ``adv_settings_auto_update`` dispatch'РёС‚ ``process_adv_v3`` С‡РµСЂРµР· ``run_tasks``."""
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    adv_setting_mock.auto_update_white_list = True
    adv_setting_mock.auto_update_target_place = True
    adv_setting_mock.auto_update_exponent = False
    adv_setting_mock.bot_active = True
    adv_setting_mock.card_ab_hold_mode = "off"
    adv_setting_mock.sales_predict_method = fact_method
    adv_setting_mock.rec_system_mode = False
    adv_setting_mock.max_place = 10
    adv_setting_mock.max_cpm = 200
    adv_setting_mock.cpm = 100
    adv_setting_mock.id = 1
    adv_setting_mock.bidder_for_auto = True
    adv_setting_mock.bidder_active = True
    adv_setting_mock.active_status = "started"

    wb_api = WBApi(access_mock, client_session_mock)

    async def _get_keywords(_: ComplexAdv, cache_only: bool = False):
        return keywords_mocks

    test_complex_adv_instance = ComplexAdv(
        shop_id=wb_api.shop_id,
        adv_setting=adv_setting_mock,
        search_adv=_search_adv_started(),
        get_keywords_func=_get_keywords,
    )

    fresh = StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)

    async def _mget_entries(_shop_id: str, adv_ids: list[int]):
        return [(aid, fresh, "hit", None) for aid in adv_ids]

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[test_complex_adv_instance]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(return_value=[None]),
        ) as run_tasks_mock,
    ):
        redis_client_wrapper = RedisClient(redis_client=fake_redis)
        plan_fact_reader = MagicMock(spec=PlanFactReader)
        plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

        manager = CoroutinesManager(
            wb_api,
            redis_client_wrapper,
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=plan_fact_reader,
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(
            side_effect=_mget_entries
        )
        await manager.adv_settings_auto_update.__wrapped__(manager, only_bot_active=True)

    run_tasks_mock.assert_called_once()
    handlers = run_tasks_mock.call_args.args[0]
    assert len(handlers) == 1
    assert callable(handlers[0])


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_get_keywords_stat_from_clickhouse_returns_data(
    clickhouse_client,
    monkeypatch: pytest.MonkeyPatch,
):
    """Seed clusters_adv_stats в†’ Act with rewritten default_db SQL в†’ assert aggregates."""
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.clusters_adv_stats")
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.adv_events_ticks")
    setup_redis_cache()
    nmid = 987_654_321
    base_date = date.today()
    # TODO: РџРµСЂРµРІРµСЃС‚Рё РїСЂРѕРµРєС‚ РЅР° СЂР°Р±РѕС‚Сѓ СЃ РґР°С‚РѕР№ РІ utc
    now_dt = datetime.now(timezone.utc)

    records = [
        ClustersAdvStatsFactory.build(
            adv_id=25040169,
            nmid=nmid,
            norm_query="test_query",
            wb_category="test_category",
            views=120,
            clicks=30,
            add_to_cart=5,
            orders=3,
            cpm=110.0,
            cpc=7.0,
            avr_pos=1.5,
            date=base_date,
            timestamp=now_dt,
        ),
        ClustersAdvStatsFactory.build(
            adv_id=25040169,
            nmid=nmid,
            norm_query="test_query",
            wb_category="test_category",
            views=80,
            clicks=20,
            add_to_cart=3,
            orders=2,
            cpm=90.0,
            cpc=6.0,
            avr_pos=2.0,
            date=base_date - timedelta(days=1),
            timestamp=now_dt - timedelta(hours=1),
        ),
    ]

    rows = build_clusters_adv_stats_rows(records)
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.clusters_adv_stats",
        rows,
        column_names=CLUSTERS_ADV_STATS_COLUMNS,
    )

    patch_get_clickhouse_client(
        monkeypatch, [calculated_keywords_manager_module], clickhouse_client
    )
    manager = CalculatedKeywordsManager()
    stats = await manager._get_keywords_stat_from_clickhouse(  # noqa
        nmids=[nmid],
        min_days=2,
        min_views=0,
    )

    assert len(stats) == 1

    keyword_stat = stats[0]
    expected_views = sum(record.views for record in records)
    expected_clicks = sum(record.clicks for record in records)
    expected_add_to_cart = sum(record.add_to_cart for record in records)
    expected_orders = sum(record.orders for record in records)
    expected_spend = sum(
        (record.cpm * record.views) / 1000
        for record in records
    )

    assert keyword_stat.text == "test_query"
    assert keyword_stat.views == expected_views
    assert keyword_stat.clicks == expected_clicks
    assert keyword_stat.add_to_cart == expected_add_to_cart
    assert keyword_stat.orders == expected_orders
    assert keyword_stat.spend == pytest.approx(expected_spend, rel=1e-4)
