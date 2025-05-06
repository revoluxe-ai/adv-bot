from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from aiogram import Bot

from app.modules.adv_creator.backend import MainAdvManager


@pytest.fixture
def bot_mock():
    bot_mock = MagicMock(spec=Bot)
    return bot_mock


@pytest.mark.asincio
async def test_create_complex_advs(access_mock, bot_mock):
    manager = MainAdvManager(access_mock)
    user_telegram_id = 122334
    nmid = 112333
    wb_api_mock = MagicMock()

    wb_api_mock.get_adv_balances = AsyncMock(return_value=1000)

    with patch(
        "app.modules.adv_creator.backend.main_manager.MainAdvManager.wb_api",
        new=wb_api_mock,
    ):
        await manager.create_complex_advs(bot_mock, user_telegram_id, nmid, None)
