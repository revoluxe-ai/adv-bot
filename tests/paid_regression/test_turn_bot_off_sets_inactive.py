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

pytestmark = [pytest.mark.unit, pytest.mark.paid_regression, pytest.mark.asyncio]


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
    adv = SimpleNamespace(id=2, bot_active=True)
    wb_user_cabinet = SimpleNamespace(id=1)

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

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            MagicMock(side_effect=sm_factory),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
            return_value=AsyncMock(),
        ),
    ):
        await turn_adv_off(call, callback_data, bot)

    assert adv.bot_active is False
    session_write.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_turn_adv_off_all_sets_all_inactive() -> None:
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=55)))
    callback_data = callbacks.TurnBot(action="off_all", wb_user_cabinet_original_id=1)
    bot = AsyncMock()
    state = AsyncMock()
    adv1 = SimpleNamespace(bot_active=True)
    adv2 = SimpleNamespace(bot_active=True)

    session = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [adv1, adv2]
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars)))
    session.commit = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            MagicMock(side_effect=lambda **_: _session_cm(session)),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.ShopMenu",
            return_value=AsyncMock(),
        ),
    ):
        await turn_adv_off_all(callback, state, callback_data, bot)

    assert adv1.bot_active is False
    assert adv2.bot_active is False
    session.commit.assert_awaited_once()
