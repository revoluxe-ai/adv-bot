"""Paid regression: turn off выставляет bot_active=False."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting.adv_setting import (
    turn_adv_off,
    turn_adv_off_all,
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
async def test_turn_adv_off_sets_bot_inactive() -> None:
    call = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=55)))
    callback_data = callbacks.TurnBot(
        action="off",
        wb_user_cabinet_original_id=1,
        adv_original_id=2,
    )
    bot = AsyncMock()
    wb_cabinet = WBCabinetFactory.build(id=10, shop_id="shop-1")
    adv = AdvSettingFactory.build(id=2, bot_active=True, wb_cabinet=wb_cabinet)
    wb_user_cabinet = SimpleNamespace(id=1, wb_cabinet=wb_cabinet)

    session_read = MagicMock()
    session_read.execute = AsyncMock(
        return_value=MagicMock(scalar=MagicMock(return_value=wb_user_cabinet))
    )
    session_write = MagicMock()
    adv_result = MagicMock()
    adv_result.scalar_one.return_value = adv
    session_write.execute = AsyncMock(return_value=adv_result)
    session_write.commit = AsyncMock()

    call_index = 0

    def sm_factory(read_only: bool = False):
        nonlocal call_index
        session = session_read if call_index == 0 else session_write
        call_index += 1
        return _session_cm(session)

    async def _deactivate(_session: MagicMock, _adv, _wb_cabinet) -> None:
        _adv.bot_active = False

    with (
        patch(
            f"{_HANDLER_MODULE}.sm",
            MagicMock(side_effect=sm_factory),
        ),
        patch(
            f"{_HANDLER_MODULE}.deactivate_adv_free_mode",
            new=AsyncMock(side_effect=_deactivate),
        ),
        patch(
            f"{_HANDLER_MODULE}.AdvSettingMenu",
            return_value=AsyncMock(),
        ),
    ):
        await turn_adv_off(call, callback_data, bot)

    assert adv.bot_active is False


@pytest.mark.asyncio
async def test_turn_adv_off_all_sets_all_inactive() -> None:
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=55)))
    callback_data = callbacks.TurnBot(action="off_all", wb_user_cabinet_original_id=1)
    bot = AsyncMock()
    state = AsyncMock()
    wb_cabinet = WBCabinetFactory.build(id=10, shop_id="shop-1")
    adv1 = AdvSettingFactory.build(id=1, bot_active=True, wb_cabinet=wb_cabinet)
    adv2 = AdvSettingFactory.build(id=2, bot_active=True, wb_cabinet=wb_cabinet)

    session = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [adv1, adv2]
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars)))
    session.commit = AsyncMock()

    with (
        patch(
            f"{_HANDLER_MODULE}.sm",
            MagicMock(side_effect=lambda **_: _session_cm(session)),
        ),
        patch(
            f"{_HANDLER_MODULE}.ShopMenu",
            return_value=AsyncMock(),
        ),
    ):
        await turn_adv_off_all(callback, state, callback_data, bot)

    assert adv1.bot_active is False
    assert adv2.bot_active is False
    session.commit.assert_awaited_once()
