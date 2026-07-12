"""Paid regression: turn on при достаточном балансе включает bot_active."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting.adv_setting import turn_adv_on
from app.client_bot.user_interface.views import callbacks

pytestmark = [pytest.mark.unit, pytest.mark.paid_regression, pytest.mark.asyncio]


def _session_cm(session: MagicMock):
    @asynccontextmanager
    async def _cm():
        yield session

    return _cm()


@pytest.mark.asyncio
async def test_turn_bot_on_sets_bot_active_when_balance_ok() -> None:
    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=101)),
    )
    callback_data = callbacks.TurnBot(
        action="on",
        wb_user_cabinet_original_id=1,
        adv_original_id=2,
    )
    bot = AsyncMock()
    state = AsyncMock()

    adv = SimpleNamespace(id=2, bot_active=False)
    wb_cabinet = SimpleNamespace(id=10, shop_id="shop-1")
    wb_user_cabinet = SimpleNamespace(wb_cabinet=wb_cabinet, id=1)

    session = MagicMock()
    session.begin = MagicMock()
    wb_uc_result = MagicMock()
    wb_uc_result.scalar_one.return_value = wb_user_cabinet
    adv_result = MagicMock()
    adv_result.scalar_one.return_value = adv
    wb_uc_result2 = MagicMock()
    wb_uc_result2.scalar_one.return_value = wb_user_cabinet
    session.execute = AsyncMock(
        side_effect=[wb_uc_result, adv_result, wb_uc_result2]
    )
    session.commit = AsyncMock()

    adv_menu_instance = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            MagicMock(side_effect=lambda **_: _session_cm(session)),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.pricer.get_price_for_day_for_shop",
            new=AsyncMock(return_value=3000),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.pricer.get_tariff_for_day",
            return_value=100.0,
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.balance_manager.get_cabinet_balance_and_bonuses",
            new=AsyncMock(return_value=(500.0, 0.0)),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
            return_value=adv_menu_instance,
        ),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    assert adv.bot_active is True
    session.commit.assert_awaited_once()
    adv_menu_instance.assert_awaited_once()
