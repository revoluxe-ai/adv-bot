"""Unit tests for mandatory phone collection middleware and handlers."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.middlewars.phone_required import PhoneRequiredMiddleware
from app.client_bot.user_interface.handlers.phone_collection import save_user_phone
from app.client_bot.user_interface.views.phone_request import get_phone_request_text
from app.utils.db.models import User
from tests.helpers.telegram_message_asserts import (
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


@pytest.fixture(autouse=True)
def mock_db_engines():
    with patch("app.utils.db.session_maker.create_async_engine") as mock_create_engine:
        mock_create_engine.return_value = AsyncMock()
    with patch("app.utils.db.session_maker.get_ssl_context") as mock_ssl_context:
        mock_ssl_context.return_value = None
    yield


def make_session_context(
    *,
    user: User | None = None,
) -> tuple[AsyncMock, AsyncGenerator[AsyncSession, None]]:
    """Build an async session context manager that returns a predefined user."""
    session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    session.execute.return_value = result_mock
    session.commit = AsyncMock()

    @asynccontextmanager
    async def session_cm(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        yield session

    return session, session_cm


def _extract_sent_text(send_message_mock: AsyncMock) -> str:
    """Return sent message text for positional and keyword bot.send_message calls."""
    args = send_message_mock.call_args.args
    kwargs = send_message_mock.call_args.kwargs
    return kwargs.get("text", args[1] if len(args) > 1 else "")


def test_phone_request_text_explains_why_contact_is_needed() -> None:
    """Phone request text should explain the reason and next step."""
    text = get_phone_request_text()
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "контакт",
            "кнопкой ниже",
            "Номер нужен для доступа",
            "обратной связи",
            "восстановления связи по заявкам",
        ],
    )
    assert_no_raw_technical_text(text)


@pytest.mark.asyncio
async def test_phone_required_middleware_blocks_message_without_phone() -> None:
    """A passed-gate user without phone gets a reply keyboard instead of handler access."""
    user = MagicMock(spec=User)
    user.passed_gate = True
    user.phone = None
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=111, username="u")
    event.chat = MagicMock(spec=Chat, id=111)
    event.contact = None
    bot = AsyncMock()
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.phone_required._sm", session_cm), patch(
        "app.client_bot.middlewars.phone_required.settings"
    ) as mock_settings:
        mock_settings.invite_gate = True
        await PhoneRequiredMiddleware()(handler, event, {"bot": bot})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.call_args.kwargs
    text = _extract_sent_text(bot.send_message)
    assert text == get_phone_request_text()
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        ["контакт", "кнопкой ниже", "Номер нужен для доступа"],
    )
    assert_no_raw_technical_text(text)
    assert_keyboard_has_buttons(kwargs["reply_markup"], ["Отправить номер телефона"])
    assert kwargs["reply_markup"].keyboard[0][0].request_contact is True


@pytest.mark.asyncio
async def test_phone_required_middleware_allows_user_with_phone() -> None:
    """A user with stored phone is not blocked."""
    user = MagicMock(spec=User)
    user.passed_gate = True
    user.phone = "+79990001122"
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=222, username="u")
    event.chat = MagicMock(spec=Chat, id=222)
    event.contact = None
    bot = AsyncMock()
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.phone_required._sm", session_cm), patch(
        "app.client_bot.middlewars.phone_required.settings"
    ) as mock_settings:
        mock_settings.invite_gate = True
        await PhoneRequiredMiddleware()(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_phone_required_middleware_skips_user_without_access() -> None:
    """A user without passed gate is ignored by the phone middleware."""
    user = MagicMock(spec=User)
    user.passed_gate = False
    user.phone = None
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=333, username="u")
    event.chat = MagicMock(spec=Chat, id=333)
    event.contact = None
    bot = AsyncMock()
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.phone_required._sm", session_cm), patch(
        "app.client_bot.middlewars.phone_required.settings"
    ) as mock_settings:
        mock_settings.invite_gate = True
        await PhoneRequiredMiddleware()(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_phone_required_middleware_blocks_callback_without_phone() -> None:
    """Callbacks are blocked and redirected to the phone request message."""
    user = MagicMock(spec=User)
    user.passed_gate = True
    user.phone = None
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=CallbackQuery)
    event.from_user = MagicMock(id=444, username="u", is_bot=False, first_name="User")
    event.id = "callback-id"
    event.chat_instance = "chat-instance"
    event.data = "adv:test"
    # MagicMock(spec=Message) omits unset attrs; production reads .date / .message_id
    # like aiogram Message (datetime) / InaccessibleMessage (int always present).
    event.message = MagicMock(spec=Message)
    event.message.message_id = 55
    event.message.date = datetime.fromtimestamp(0, tz=timezone.utc)
    event.message.chat = MagicMock(spec=Chat, id=444, type="private")
    bot = AsyncMock()
    handler = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()

    with patch("app.client_bot.middlewars.phone_required._sm", session_cm), patch(
        "app.client_bot.middlewars.phone_required.settings"
    ) as mock_settings:
        mock_settings.invite_gate = True
        await PhoneRequiredMiddleware()(handler, event, {"bot": bot, "state": state})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.call_args.kwargs
    assert_message_within_telegram_limit(_extract_sent_text(bot.send_message))
    assert_keyboard_has_buttons(kwargs["reply_markup"], ["Отправить номер телефона"])
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_user_phone_saves_own_contact() -> None:
    """The handler stores the user's own contact and removes the reply keyboard."""
    user = MagicMock(spec=User)
    user.phone = None
    session, session_cm = make_session_context(user=user)

    message = MagicMock(spec=Message)
    message.chat = MagicMock(spec=Chat, id=555)
    message.from_user = MagicMock(id=555)
    message.contact = MagicMock(user_id=555, phone_number="+79990001122")
    message.message_id = 99
    bot = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    dispatcher = AsyncMock()

    with patch("app.client_bot.user_interface.handlers.phone_collection._sm", session_cm):
        await save_user_phone(message, bot, state, dispatcher)

    assert user.phone == "+79990001122"
    session.commit.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["reply_markup"].remove_keyboard is True
    dispatcher.feed_update.assert_not_called()


@pytest.mark.asyncio
async def test_save_user_phone_rejects_foreign_contact() -> None:
    """A foreign contact is rejected and does not trigger DB writes."""
    user = MagicMock(spec=User)
    session, session_cm = make_session_context(user=user)

    message = MagicMock(spec=Message)
    message.chat = MagicMock(spec=Chat, id=666)
    message.from_user = MagicMock(id=666)
    message.contact = MagicMock(user_id=777, phone_number="+79990001122")
    bot = AsyncMock()
    state = MagicMock(spec=FSMContext)
    dispatcher = AsyncMock()

    with patch("app.client_bot.user_interface.handlers.phone_collection._sm", session_cm):
        await save_user_phone(message, bot, state, dispatcher)

    session.commit.assert_not_awaited()
    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_user_phone_replays_pending_callback() -> None:
    """Saved contact replays the callback that had been blocked by phone gating."""
    user = MagicMock(spec=User)
    user.phone = None
    session, session_cm = make_session_context(user=user)

    message = MagicMock(spec=Message)
    message.chat = MagicMock(spec=Chat, id=777)
    message.from_user = MagicMock(id=777)
    message.contact = MagicMock(user_id=777, phone_number="+79990001122")
    message.message_id = 1234
    bot = AsyncMock()
    state = MagicMock()
    pending_callback = {
        "id": "callback-id",
        "from_user": {"id": 777, "is_bot": False, "first_name": "Test"},
        "chat_instance": "chat-instance",
        "data": "adv:test",
        "message": {"message_id": 55, "date": 0, "chat": {"id": 777, "type": "private"}},
    }
    state.get_data = AsyncMock(
        return_value={"pending_phone_callback": json.dumps(pending_callback)}
    )
    state.update_data = AsyncMock()
    dispatcher = AsyncMock()

    with patch("app.client_bot.user_interface.handlers.phone_collection._sm", session_cm), patch(
        "app.client_bot.user_interface.handlers.phone_collection.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        await save_user_phone(message, bot, state, dispatcher)

    mock_sleep.assert_awaited_once_with(0.3)
    dispatcher.feed_update.assert_awaited_once()
    replay_kwargs = dispatcher.feed_update.call_args.kwargs
    replay_update = (
        replay_kwargs["update"]
        if "update" in replay_kwargs
        else dispatcher.feed_update.call_args.args[1]
    )
    assert replay_update.callback_query is not None
    assert replay_update.callback_query.data == "adv:test"
    state.update_data.assert_awaited_once_with(pending_phone_callback=None)
