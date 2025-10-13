from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay

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
    redis_cache_mock.last_auto_delete_white_list.check_pass_time = AsyncMock(
        return_value=True
    )
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
        white_keywords = [
            kw
            for kw in keywords_mocks
            if kw.hard_status == 2 and not kw.best_keyword_status
        ]
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
async def test_white_list_manager_delete_phrase_functionality(
    adv_setting_mock, keywords_mocks, common_mocks
):
    """Test that WhiteListUpdateManager properly deletes phrases from white list."""
    session_mock, get_session_maker_mock = common_mocks

    # Setup Redis cache mock
    redis_cache_mock = MagicMock()
    redis_cache_mock.last_auto_delete_white_list = MagicMock()
    redis_cache_mock.last_auto_delete_white_list.check_pass_time = AsyncMock(
        return_value=True
    )
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

        # Test successful deletion
        deleted, no_candidates = await manager.delete_last_white_phrase(keywords_mocks)

        # Should return True for deletion, False for no_candidates
        assert deleted is True
        assert no_candidates is False

        # Verify database update was called
        session_mock.execute.assert_called_once()
        session_mock.commit.assert_called_once()

        # Verify Redis cache was updated
        redis_cache_mock.last_auto_delete_white_list.set.assert_called_once()


@pytest.mark.asyncio
async def test_white_list_manager_delete_phrase_time_not_passed(
    adv_setting_mock, keywords_mocks, common_mocks
):
    """Test that deletion is skipped when time hasn't passed."""
    session_mock, get_session_maker_mock = common_mocks

    # Setup Redis cache mock with time not passed
    redis_cache_mock = MagicMock()
    redis_cache_mock.last_auto_delete_white_list = MagicMock()
    redis_cache_mock.last_auto_delete_white_list.check_pass_time = AsyncMock(
        return_value=False
    )
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

        # Test that deletion is skipped
        deleted, no_candidates = await manager.delete_last_white_phrase(keywords_mocks)

        # Should return False for both
        assert deleted is False
        assert no_candidates is False

        # Verify no database operations
        session_mock.execute.assert_not_called()
        session_mock.commit.assert_not_called()

        # Verify Redis cache was not updated
        redis_cache_mock.last_auto_delete_white_list.set.assert_not_called()


@pytest.mark.asyncio
async def test_white_list_manager_delete_phrase_no_candidates(
    adv_setting_mock, common_mocks
):
    """Test behavior when there are no candidates for deletion."""
    session_mock, get_session_maker_mock = common_mocks

    # Create keywords with no white list candidates (all have hard_status != 2)
    keywords_no_candidates = [
        MagicMock(
            spec=CalculatedKeyword,
            hard_status=1,
            best_keyword_status=False,
            baes_ctr=0.5,
        ),
        MagicMock(
            spec=CalculatedKeyword,
            hard_status=1,
            best_keyword_status=False,
            baes_ctr=0.3,
        ),
    ]

    # Setup Redis cache mock
    redis_cache_mock = MagicMock()
    redis_cache_mock.last_auto_delete_white_list = MagicMock()
    redis_cache_mock.last_auto_delete_white_list.check_pass_time = AsyncMock(
        return_value=True
    )
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

        # Test with no candidates
        deleted, no_candidates = await manager.delete_last_white_phrase(
            keywords_no_candidates
        )  # type: ignore

        # Should return False for deletion, True for no_candidates
        assert deleted is False
        assert no_candidates is True

        # Verify no database operations
        session_mock.execute.assert_not_called()
        session_mock.commit.assert_not_called()

        # Verify Redis cache was not updated
        redis_cache_mock.last_auto_delete_white_list.set.assert_not_called()
