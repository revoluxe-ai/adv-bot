from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot

from app.core.wb_api.data_classes.advs.base_adv import Adv
from app.modules.adv_creator.backend import MainAdvManager


@pytest.fixture
def bot_mock():
    bot_mock = MagicMock(spec=Bot)
    return bot_mock


@pytest.fixture
def client_session_mock():
    session = AsyncMock()
    session.close = MagicMock()
    return session


@pytest.mark.asyncio
async def test_create_complex_advs(
    access_mock, adv_setting_mock, bot_mock, client_session_mock
):
    user_telegram_id = 122334
    nmid = 112333

    with (
        patch("app.modules.adv_creator.backend.main_manager.WBApi") as WBAPI_mock,
    ):
        MainAdvManager.get_adv_setting_by_nmid = AsyncMock(
            return_value=adv_setting_mock
        )
        MainAdvManager.start_complex_advs = AsyncMock()
        manager = MainAdvManager(access_mock, client_session_mock)

        manager.upcast_auto_adv = AsyncMock(return_value=None)

        WBAPI_mock.get_adv_balances = AsyncMock(return_value=1000)
        adv_from_wb_mock_1 = MagicMock(spec=Adv)
        adv_from_wb_mock_2 = MagicMock(spec=Adv)

        WBAPI_mock.get_advs = AsyncMock(
            return_value=[adv_from_wb_mock_1, adv_from_wb_mock_2]
        )
        manager.get_adv_setting_by_nmid = AsyncMock(return_value=adv_setting_mock)
        await manager.create_complex_advs(bot_mock, user_telegram_id, nmid, None)
