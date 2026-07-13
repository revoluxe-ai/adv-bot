"""Paid regression: turn on блокируется при недостаточном балансе."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting.adv_setting import turn_adv_on
from app.client_bot.user_interface.services.adv_auto_management_activation import (
    PaidActivationBlockReason,
    PaidActivationEligibility,
)
from app.client_bot.user_interface.views import callbacks
from tests.factories.adv_factory import AdvSettingFactory, WBCabinetFactory

pytestmark = [pytest.mark.unit, pytest.mark.paid_regression, pytest.mark.asyncio]

_HANDLER_MODULE = "app.client_bot.user_interface.handlers.adv_setting.adv_setting"


def _session_cm(session: MagicMock):
    @asynccontextmanager
    async def _cm():
        yield session

    return _cm()


@pytest.mark.asyncio
async def test_turn_bot_on_rejects_insufficient_balance() -> None:
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

    wb_cabinet = WBCabinetFactory.build(id=10, shop_id="shop-1")
    adv = AdvSettingFactory.build(id=2, bot_active=False, wb_cabinet=wb_cabinet)
    wb_user_cabinet = SimpleNamespace(wb_cabinet=wb_cabinet)

    session = MagicMock()
    session.begin = AsyncMock()
    wb_uc_result = MagicMock()
    wb_uc_result.scalar_one.return_value = wb_user_cabinet
    adv_result = MagicMock()
    adv_result.scalar_one.return_value = adv
    session.execute = AsyncMock(side_effect=[wb_uc_result, adv_result])
    session.commit = AsyncMock()
    activate_mock = AsyncMock()

    with (
        patch(
            f"{_HANDLER_MODULE}.sm",
            MagicMock(side_effect=lambda **_: _session_cm(session)),
        ),
        patch(
            f"{_HANDLER_MODULE}.check_paid_activation_eligibility",
            new=AsyncMock(
                return_value=PaidActivationEligibility(
                    allowed=False,
                    block_reason=PaidActivationBlockReason.ZERO_BALANCE,
                )
            ),
        ),
        patch(f"{_HANDLER_MODULE}.activate_adv_paid_mode", activate_mock),
        patch(
            f"{_HANDLER_MODULE}.ShopMenu",
            return_value=AsyncMock(),
        ),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    assert adv.bot_active is False
    activate_mock.assert_not_awaited()
    bot.send_message.assert_awaited()
