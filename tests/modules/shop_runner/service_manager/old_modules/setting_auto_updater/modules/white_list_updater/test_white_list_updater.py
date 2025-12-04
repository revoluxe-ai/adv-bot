"""Тесты для WhiteListUpdateManager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.auto_white_list_updater import (
    WhiteListUpdateManager,
)


AUTO_ADV_ID = 25031215

# Путь к модулю для патчинга
MODULE_PATH = (
    "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater"
    ".modules.white_list_updater.auto_white_list_updater.auto_white_list_updater"
)


@pytest.fixture
def adv_setting_mock():
    """Мок для AdvSetting."""
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.nmids = [123456789]
    adv_setting.adv_id = AUTO_ADV_ID
    adv_setting.auction_adv_id = 25031147
    adv_setting.max_pay_for_order = 200
    adv_setting.auto_update_white_list = True
    return adv_setting


@pytest.fixture
def common_mocks():
    """Общие моки для сессии БД."""
    session_mock = MagicMock()
    session_mock.execute = AsyncMock()
    session_mock.flush = AsyncMock()
    session_mock.commit = AsyncMock()
    session_maker_mock = MagicMock()
    session_maker_mock.__aenter__ = AsyncMock(return_value=session_mock)
    get_session_maker_mock = MagicMock(return_value=session_maker_mock)
    return session_mock, get_session_maker_mock


@pytest.fixture
def redis_cache_mock_pass_time():
    """Мок Redis cache с пройденным временем."""
    redis_cache_mock = MagicMock()
    redis_cache_mock.last_auto_delete_white_list = MagicMock()
    redis_cache_mock.last_auto_delete_white_list.check_pass_time = AsyncMock(
        return_value=True
    )
    redis_cache_mock.last_auto_delete_white_list.set = AsyncMock()
    return redis_cache_mock


@pytest.fixture
def redis_cache_mock_not_pass_time():
    """Мок Redis cache с не пройденным временем."""
    redis_cache_mock = MagicMock()
    redis_cache_mock.last_auto_delete_white_list = MagicMock()
    redis_cache_mock.last_auto_delete_white_list.check_pass_time = AsyncMock(
        return_value=False
    )
    redis_cache_mock.last_auto_delete_white_list.set = AsyncMock()
    return redis_cache_mock


@pytest.mark.asyncio
async def test_update_white_list_deletes_last_keyword(
    common_mocks,
    keywords_mocks,
    adv_setting_mock,
    redis_cache_mock_pass_time,
):
    """Тест проверяет, что метод delete_last_white_phrase удаляет последний keyword из белого списка."""
    session_mock, get_session_maker_mock = common_mocks

    with (
        patch(f"{MODULE_PATH}.sm", new=get_session_maker_mock),
        patch(
            f"{MODULE_PATH}.AdvSettingRedisCache",
            return_value=redis_cache_mock_pass_time,
        ),
    ):
        manager = WhiteListUpdateManager(adv_setting_mock)
        deleted, no_candidates = await manager.delete_last_white_phrase(keywords_mocks)

        # Проверяем что удаление произошло (есть 5 keywords с hard_status=2)
        # После фильтрации и удаления первого (лучшего), остаётся 4 кандидата
        assert deleted is True
        assert no_candidates is False

        # DB update executed via session.execute and committed
        assert session_mock.execute.call_count == 1
        assert session_mock.commit.call_count == 1
        assert redis_cache_mock_pass_time.last_auto_delete_white_list.set.call_count == 1


@pytest.mark.asyncio
async def test_white_list_manager_delete_phrase_functionality(
    adv_setting_mock,
    keywords_mocks,
    common_mocks,
    redis_cache_mock_pass_time,
):
    """Test that WhiteListUpdateManager properly deletes phrases from white list."""
    session_mock, get_session_maker_mock = common_mocks

    with (
        patch(f"{MODULE_PATH}.sm", new=get_session_maker_mock),
        patch(
            f"{MODULE_PATH}.AdvSettingRedisCache",
            return_value=redis_cache_mock_pass_time,
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
        redis_cache_mock_pass_time.last_auto_delete_white_list.set.assert_called_once()


@pytest.mark.asyncio
async def test_white_list_manager_delete_phrase_time_not_passed(
    adv_setting_mock,
    keywords_mocks,
    common_mocks,
    redis_cache_mock_not_pass_time,
):
    """Test that deletion is skipped when time hasn't passed."""
    session_mock, get_session_maker_mock = common_mocks

    with (
        patch(f"{MODULE_PATH}.sm", new=get_session_maker_mock),
        patch(
            f"{MODULE_PATH}.AdvSettingRedisCache",
            return_value=redis_cache_mock_not_pass_time,
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
        redis_cache_mock_not_pass_time.last_auto_delete_white_list.set.assert_not_called()


@pytest.mark.asyncio
async def test_white_list_manager_delete_phrase_no_candidates(
    adv_setting_mock,
    common_mocks,
    redis_cache_mock_pass_time,
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

    with (
        patch(f"{MODULE_PATH}.sm", new=get_session_maker_mock),
        patch(
            f"{MODULE_PATH}.AdvSettingRedisCache",
            return_value=redis_cache_mock_pass_time,
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
        redis_cache_mock_pass_time.last_auto_delete_white_list.set.assert_not_called()



