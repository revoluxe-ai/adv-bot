from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, Update, User
from aiogram.types.error_event import ErrorEvent

from app.client_bot.user_interface.handlers import exceptions as exc_mod


pytestmark = pytest.mark.unit


def _make_error_event(exc: Exception, chat_id: int = 1001) -> ErrorEvent:
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=int(datetime.now().timestamp()),
            chat=Chat(id=chat_id, type="private"),
            from_user=User(id=chat_id, is_bot=False, first_name="u"),
            text="/x",
        ),
    )
    return ErrorEvent(update=update, exception=exc)


@pytest.mark.asyncio
async def test_bad_request_message_too_long_is_handled() -> None:
    marker = "PAYLOAD_MARKER"
    long_payload = marker + ("X" * 4500)
    exc = TelegramBadRequest(
        method=SendMessage(chat_id=1001, text=long_payload),
        message="Bad Request: message is too long",
    )
    event = _make_error_event(exc)

    sent: list[tuple[int, str]] = []

    async def send_message(chat_id: int, text: str, **_kwargs: object) -> MagicMock:
        sent.append((int(chat_id), text))
        return MagicMock()

    bot = MagicMock()
    bot.send_message = AsyncMock(side_effect=send_message)
    state = MagicMock()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(exc_mod, "admin_telegram_id", 999999)
    try:
        await exc_mod.error_handler_for_telegram_bad_request_exception(event, state, bot)
    finally:
        monkeypatch.undo()

    admin_text = "".join(text for chat_id, text in sent if chat_id == 999999)
    assert "message is too long" in admin_text
    assert marker in admin_text
    assert any(chat_id == 1001 for chat_id, _ in sent)


@pytest.mark.asyncio
async def test_bad_request_other_message_is_skipped() -> None:
    exc = TelegramBadRequest(
        method=SendMessage(chat_id=1001, text="hello"),
        message="Bad Request: chat not found",
    )
    event = _make_error_event(exc)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()

    with pytest.raises(SkipHandler):
        await exc_mod.error_handler_for_telegram_bad_request_exception(event, state, bot)
