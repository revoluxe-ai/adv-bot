from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
    FactData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
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
    get_async_session_mock,
    fake_redis,
    di_containner_for_adv_auto_updater_v2,
):
    adv_setting_mock.auto_update_white_list = True
    adv_setting_mock.auto_update_target_place = True
    adv_setting_mock.auto_update_exponent = False
    adv_setting_mock.automatic_version = 1
    adv_setting_mock.auto_updater_version = 1
    adv_setting_mock.sales_predict_method = fact_method
    adv_setting_mock.rec_system_mode = False
    adv_setting_mock.max_place = 10
    adv_setting_mock.max_cpm = 200
    adv_setting_mock.cpm = 100
    adv_setting_mock.id = 1
    adv_setting_mock.bidder_for_auto = True
    adv_setting_mock.bidder_active = True
    adv_setting_mock.bot_active = True
    _ = di_containner_for_adv_auto_updater_v2

    wb_api = WBApi(access_mock, client_session_mock)

    async def _get_keywords(_: ComplexAdv, cache_only: bool = False):
        return keywords_mocks

    test_complex_adv_instance = ComplexAdv(
        shop_id=wb_api.shop_id,
        adv_setting=adv_setting_mock,
        search_adv=None,
        get_keywords_func=_get_keywords,
    )

    data_manager_mock = MagicMock()
    data_manager_mock.get_good_bad_phrases = AsyncMock(return_value=keywords_mocks)
    plan_data = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=250)

    fact_data = FactData(
        predict_orders=1, pay_for_order=100, original_orders=1, fact_method=fact_method
    )

    # Мок для ChangePlanFact
    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock(return_value=None)

    with (
        patch(
            "app.utils.db.session_maker.get_async_session_maker",
            new=get_async_session_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_version_migration.sm",
            new=get_async_session_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager._get_adv_id_to_search_adv_map",
            new=AsyncMock(return_value={}), # Возвращаем пустой словарь AdvSetting
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater.AdvSettingAutoUpdater.get_fact_data",
            new=AsyncMock(return_value=fact_data),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater.AdvSettingAutoUpdater.get_plan_data",
            new=MagicMock(return_value=plan_data),
        ),
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[test_complex_adv_instance]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater.AdvSettingAutoUpdater.update",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater."
            "auto_white_list_updater.auto_white_list_updater.WhiteListUpdateManager.delete_last_white_phrase",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater."
            "auto_white_list_updater.auto_white_list_updater.WhiteListUpdateManager.delete_last_white_phrase"
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            new=get_async_session_mock,
        ),
    ):
        redis_client_wrapper = RedisClient(redis_client=fake_redis)
        plan_fact_reader = MagicMock(spec=PlanFactReader)
        plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

        wb_manager_hub = MagicMock()
        wb_manager_hub.wb_data_manager = MagicMock()
        wb_manager_hub.wb_manager = MagicMock()

        manager = CoroutinesManager(
            wb_api,
            redis_client_wrapper,
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=plan_fact_reader,
            wb_manager_hub=wb_manager_hub,
        )
        manager._update_advs_models = AsyncMock()
        manager._adv_settings_list = [adv_setting_mock]
        manager._adv_settings_dict = {adv_setting_mock.adv_id: adv_setting_mock}
        # decorator while_coroutine_decorator запускает корутину в бесконечном цикле,
        # поэтому в тестах мы вызываем оригинальную функцию через __wrapped__,
        # чтобы выполнить её один раз и не зависнуть.
        await manager.adv_settings_auto_update.__wrapped__(manager, only_bot_active=True)  # noqa


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_get_keywords_stat_from_clickhouse_returns_data(
    clickhouse_client,
    monkeypatch: pytest.MonkeyPatch,
):
    """Seed clusters_adv_stats → Act with rewritten default_db SQL → assert aggregates."""
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.clusters_adv_stats")
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.adv_events_ticks")
    setup_redis_cache()
    nmid = 987_654_321
    base_date = date.today()
    # TODO: Перевести проект на работу с датой в utc
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
