from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from .auto_white_list_updater import WhiteListUpdateManager
from app.modules.shop_runner.wb_shop import WBShop

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

    redis_manager_mock = MagicMock()
    redis_manager_mock.get_last_spend_sum = AsyncMock(return_value=redis_sum)
    redis_manager_mock.set_last_spend_sum = AsyncMock()

    click_house_manager_mock = MagicMock()
    click_house_manager_mock.get_sum_spend_for_complex_adv = AsyncMock(
        return_value=clickhouse_sum
    )

    with (
        patch(
            "app.modules.shop_runner.modules.auto_white_list_updater.auto_white_list_updater.sm",
            new=get_session_maker_mock,
        ),
        patch(
            "app.modules.shop_runner.modules.auto_white_list_updater."
            "auto_white_list_updater.WhiteListDeleteManager.redis_manager",
            new=redis_manager_mock,
        ),
        patch(
            "app.modules.shop_runner.modules.auto_white_list_updater.auto_white_list_updater.click_house_manager",
            new=click_house_manager_mock,
        ),
        patch(
            "app.modules.shop_runner.modules."
            "auto_white_list_updater.auto_white_list_updater.get_daily_stats_by_last_days",
            new=get_daily_stats_by_last_days_mock,
        ),
    ):
        manager = WhiteListUpdateManager()
        await manager.auto_update_phrases_in_white_list(
            adv_setting_mock, keywords_mocks
        )

        if expected_change:
            assert session_mock.add.call_count == 1
            assert session_mock.flush.call_count == 1
            assert session_mock.commit.call_count == 1
            assert keywords_mocks[-2].hard_status == 1
            assert redis_manager_mock.set_last_spend_sum.await_args(
                auto_adv_id, clickhouse_sum
            )

        else:
            assert session_mock.add.call_count == 0
            assert session_mock.flush.call_count == 0
            assert session_mock.commit.call_count == 0
            assert keywords_mocks[-2].hard_status == 2
            assert redis_manager_mock.set_last_spend_sum.call_count == 0


@pytest.mark.asyncio
async def test_WBShop_delete_phrase_from_white_list_run(
    adv_setting_mock, keywords_mocks
):

    wb_shop = WBShop("тест shop_id", 123456)
    wb_shop._update_advs_models = AsyncMock()
    wb_shop._adv_settings = [adv_setting_mock]
    wb_shop._update_phrases_in_white_list_run()
    wb_shop.get_calculated_keywords = AsyncMock(return_value=keywords_mocks)
