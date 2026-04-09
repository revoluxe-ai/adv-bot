from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery

from app.client_bot.user_interface.handlers.request_presentation import (
    request_presentation_start,
)


@pytest.mark.asyncio
async def test_request_presentation_start_no_invite_required() -> None:
    bot = AsyncMock()
    state = AsyncMock()
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(id=123456, username="tester")
    callback.message = MagicMock()
    callback.message.chat.id = 123456
    callback.answer = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.request_presentation.notify_presentation_request",
        new=AsyncMock(),
    ) as notify_mock:
        await request_presentation_start(callback, bot, state)

    state.clear.assert_awaited_once()
    notify_mock.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    call_args, call_kwargs = bot.send_message.call_args
    assert call_args[0] == 123456
    assert "Заявка отправлена менеджеру" in call_args[1]
    assert call_kwargs["reply_markup"] is not None
    callback.answer.assert_awaited_once()
