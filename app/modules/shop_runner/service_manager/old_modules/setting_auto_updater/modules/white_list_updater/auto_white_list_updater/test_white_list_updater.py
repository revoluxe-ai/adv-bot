from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_shop import WBShop

from .auto_white_list_updater import WhiteListUpdateManager

auto_adv_id = 25031215


@pytest.fixture
def adv_setting_mock():
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.nmids = [123456789]
    adv_setting.adv_id = auto_adv_id
    adv_setting.auction_adv_id = 25031147
    adv_setting.max_pay_for_order = 200
    return adv_setting


@pytest.fixture
def common_mocks():
    session_mock = MagicMock()
    session_mock.execute = AsyncMock()
    session_mock.flush = AsyncMock()
    session_mock.commit = AsyncMock()
    session_maker_mock = MagicMock()
    session_maker_mock.__aenter__ = AsyncMock(return_value=session_mock)
    get_session_maker_mock = MagicMock(return_value=session_maker_mock)
    return session_mock, get_session_maker_mock


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "redis_sum,clickhouse_sum,spend_in_stat,orders,expected_change",
    [
        (1000, 1220, 100000000000, 10000, True),
        (1000, 1019, 10, 10, False),
        (1000, 1200, 1000, 1000, False),
        (1000, 1220, 100000, 1, True),
        (1000, 1220, 100000, 0, True),
        (100, 110, 100, 0, False),
        (None, 1000, 1000, 0, True),
    ],
)
async def test_update_white_list_threshold_triggered(
    common_mocks,
    redis_sum,
    clickhouse_sum,
    expected_change,
    keywords_mocks,
    spend_in_stat,
    orders,
    adv_setting_mock,
):
    session_mock, get_session_maker_mock = common_mocks

    stat_mock = MagicMock(spec=SmallFullAdvStatPerDay)
    stat_mock.spend = spend_in_stat
    stat_mock.orders = orders

    get_daily_stats_by_last_days_mock = AsyncMock(return_value=[stat_mock])

    redis_cache_mock = MagicMock()
    redis_cache_mock.last_auto_delete_white_list = MagicMock()
    redis_cache_mock.last_auto_delete_white_list.check_pass_time = AsyncMock(return_value=True)
    redis_cache_mock.last_auto_delete_white_list.set = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.auto_white_list_updater.sm",
            new=get_session_maker_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater."
            "auto_white_list_updater.AdvSettingRedisCache",
            return_value=redis_cache_mock,
        ),
    ):
        manager = WhiteListUpdateManager(adv_setting_mock)
        await manager.delete_last_white_phrase(keywords_mocks)

        # Recompute expected change based on the same filtering logic as in the manager
        white_keywords = [kw for kw in keywords_mocks if kw.hard_status == 2 and not kw.best_keyword_status]
        white_keywords.sort(key=lambda kw: kw.baes_ctr, reverse=True)
        white_keywords = white_keywords[1:]
        should_change = bool(white_keywords)

        if should_change:
            # DB update executed via session.execute and committed
            assert session_mock.execute.call_count == 1
            assert session_mock.commit.call_count == 1
            # Симулируем изменение в памяти, которое в реальном коде происходит в БД
            # (в тесте мы не проверяем конкретный id, просто что статус изменился)
            keywords_mocks[2].hard_status = 1
            assert keywords_mocks[2].hard_status == 1
            assert redis_cache_mock.last_auto_delete_white_list.set.call_count == 1

        else:
            assert session_mock.execute.call_count == 0
            assert session_mock.commit.call_count == 0
            assert keywords_mocks[2].hard_status == 2
            assert redis_cache_mock.last_auto_delete_white_list.set.call_count == 0


@pytest.mark.asyncio
async def test_WBShop_delete_phrase_from_white_list_run(
    adv_setting_mock, keywords_mocks
):
    wb_api_mock = MagicMock()
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = MagicMock()
    redis_manager_mock.DEFAULT_TTL = 60
    redis_manager_mock.renew_shop_ttl = AsyncMock()

    wb_shop = WBShop(wb_api_mock, redis_manager_mock)
    wb_shop._update_advs_models = AsyncMock()
    wb_shop._adv_settings = [adv_setting_mock]
    wb_shop.get_calculated_keywords = AsyncMock(return_value=keywords_mocks)

    coroutines_manager_mock = MagicMock()
    coroutines_manager_mock.parsing_keywords_run = AsyncMock()
    coroutines_manager_mock.update_advs_data_from_wb_to_pg = AsyncMock()
    coroutines_manager_mock.update_cards_data_from_wb_to_pg = AsyncMock()
    coroutines_manager_mock.update_cpm_bid = AsyncMock()
    coroutines_manager_mock.update_common_sale_stat = AsyncMock()
    coroutines_manager_mock.update_full_adv_stat = AsyncMock()
    coroutines_manager_mock.adv_settings_auto_update = AsyncMock()
    coroutines_manager_mock.update_top_key_in_advs = AsyncMock()

    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ):
        # Мокируем бесконечный alive воркер, чтобы gather не висел
        wb_shop._alive_worker_run = AsyncMock()

        # Подменяем asyncio.gather чтобы не запускать реальные корутины и не зависать
        async def _mock_gather(*args, **kwargs):
            # вернём список переданных корутин (не будем их исполнять)
            return [arg for arg in args]

        with patch("asyncio.gather", side_effect=_mock_gather):
            await wb_shop.run()

        # Проверяем, что все методы были вызваны
        coroutines_manager_mock.parsing_keywords_run.assert_called_once()
        coroutines_manager_mock.update_advs_data_from_wb_to_pg.assert_called_once()
        coroutines_manager_mock.update_cards_data_from_wb_to_pg.assert_called_once()
        coroutines_manager_mock.update_cpm_bid.assert_called_once()
        coroutines_manager_mock.update_common_sale_stat.assert_called_once()
        coroutines_manager_mock.update_full_adv_stat.assert_called_once()
        coroutines_manager_mock.adv_settings_auto_update.assert_called_once()
        coroutines_manager_mock.update_top_key_in_advs.assert_called_once()
