"""Unit tests for invite gate text, keyboard, and middleware behavior."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message
from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.const import ADMINS, SUPPORT_USER_NAME
from app.client_bot.middlewars.gate import GateMiddleware
from app.client_bot.start_command import is_start_command_message
from app.client_bot.user_interface.views.callbacks import Gate
from app.client_bot.user_interface.views.gate import (
    get_gate_keyboard,
    get_gate_message_text,
)
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
    result: MagicMock | None = None,
) -> tuple[AsyncMock, AsyncGenerator[AsyncSession, None]]:
    session = AsyncMock(spec=AsyncSession)
    result_mock = result or MagicMock(spec=Result)
    if result is None:
        result_mock.scalar_one_or_none.return_value = user
    session.execute.return_value = result_mock
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    @asynccontextmanager
    async def session_cm(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        yield session

    return session, session_cm


def _extract_sent_text(send_message_mock: AsyncMock) -> str:
    """Return sent message text for positional and keyword bot.send_message calls."""
    args = send_message_mock.call_args.args
    kwargs = send_message_mock.call_args.kwargs
    return kwargs.get("text", args[1] if len(args) > 1 else "")


def test_get_gate_message_text_contains_header_and_invite() -> None:
    text = get_gate_message_text()
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        ["инвайт"],
    )
    assert_no_raw_technical_text(text)



@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_is_start_command_empty_or_whitespace_returns_false(text: str) -> None:
    """Empty/whitespace text must not crash split logic."""
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.caption = None
    assert is_start_command_message(msg) is False


def test_get_gate_keyboard_has_three_buttons() -> None:
    kb = get_gate_keyboard()
    assert_keyboard_has_buttons(kb, ["Ввести инвайт", "Оферта", "Восстановить доступ"])
    assert len(kb.inline_keyboard) == 3
    assert kb.inline_keyboard[0][0].callback_data == Gate(action="invite_enter").pack()
    assert kb.inline_keyboard[2][0].url is not None
    assert kb.inline_keyboard[2][0].url.startswith(f"https://t.me/{SUPPORT_USER_NAME}")


@pytest.mark.asyncio
async def test_gate_middleware_passed_gate_calls_handler() -> None:
    """A passed-gate user is allowed through middleware."""
    user = MagicMock(spec=User)
    user.passed_gate = True
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=123, is_bot=False, username="test_user_123")
    event.chat = MagicMock(spec=Chat, id=123)
    data = {"bot": AsyncMock()}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = False
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)


@pytest.mark.asyncio
async def test_gate_middleware_gate_callback_passed_through() -> None:
    """gate:* callback is allowed even before passed_gate."""
    user = MagicMock(spec=User)
    user.passed_gate = False
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=CallbackQuery)
    event.from_user = MagicMock(id=789, is_bot=False, username="test_user_789")
    event.data = Gate(action="invite_enter").pack()
    event.message = MagicMock(spec=Message)
    event.message.chat = MagicMock(spec=Chat, id=789)
    data = {"bot": AsyncMock()}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = False
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)


@pytest.mark.asyncio
async def test_gate_middleware_admin_bypass() -> None:
    """Admin is always allowed through."""
    if not ADMINS:
        pytest.skip("ADMINS пустой")

    user = MagicMock(spec=User)
    user.passed_gate = False
    _, session_cm = make_session_context(user=user)
    admin_id = ADMINS[0]

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=admin_id, is_bot=False, username="test_admin_user")
    event.chat = MagicMock(spec=Chat, id=admin_id)
    event.text = "любой текст"
    event.successful_payment = None
    data = {"bot": AsyncMock()}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm):
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)


@pytest.mark.asyncio
async def test_gate_middleware_new_user_creation_and_gate_screen() -> None:
    """A new user is created and receives the gate screen."""
    handler = AsyncMock()
    telegram_id = 1011
    username = "new_test_user"
    chat_id = 1011

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=telegram_id, is_bot=False, username=username)
    event.chat = MagicMock(spec=Chat, id=chat_id)
    event.successful_payment = None
    bot_mock = AsyncMock()
    session_mock, session_cm = make_session_context(user=None)
    data = {"bot": bot_mock}

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.invite_gate = True
        mock_settings.presentation_only = False
        result = await GateMiddleware()(handler, event, data)

    assert result is None
    session_mock.add.assert_called_once()
    added_user = session_mock.add.call_args.args[0]
    assert isinstance(added_user, User)
    assert added_user.user_telegram_id == telegram_id
    assert added_user.username == username
    assert added_user.adv_updater_user_chat_id == chat_id
    session_mock.commit.assert_awaited_once()
    session_mock.refresh.assert_awaited_once_with(added_user)
    bot_mock.send_message.assert_awaited_once()
    kwargs = bot_mock.send_message.call_args.kwargs
    assert_message_within_telegram_limit(_extract_sent_text(bot_mock.send_message))
    assert_keyboard_has_buttons(kwargs["reply_markup"], ["Ввести инвайт", "Оферта", "Восстановить доступ"])
    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_gate_middleware_successful_payment_passes_through() -> None:
    """successful_payment message bypasses the gate."""
    user = MagicMock(spec=User)
    user.passed_gate = False
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=12345, is_bot=False, username="test_user_12345")
    event.chat = MagicMock(spec=Chat, id=12345)
    event.successful_payment = MagicMock()
    data = {"bot": AsyncMock()}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = False
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)


@pytest.mark.asyncio
async def test_gate_middleware_legacy_presentation_flag_passed_gate_allows_handler() -> None:
    """Legacy PRESENTATION_ONLY=true does not change passed_gate bypass."""
    user = MagicMock(spec=User)
    user.passed_gate = True
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=888002, is_bot=False, username="u")
    event.chat = MagicMock(spec=Chat, id=888002)
    event.text = "любой текст"
    event.successful_payment = None
    data = {"bot": AsyncMock(), "state": None}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = True
        mock_settings.invite_gate = True
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)


@pytest.mark.asyncio
async def test_gate_middleware_legacy_presentation_flag_blocks_unknown_message() -> None:
    """Legacy PRESENTATION_ONLY=true still uses invite-gate block path."""
    user = MagicMock(spec=User)
    user.passed_gate = False
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=999001, is_bot=False, username="u")
    event.chat = MagicMock(spec=Chat, id=999001)
    event.text = "произвольный текст"
    event.successful_payment = None
    bot = AsyncMock()
    data = {"bot": bot, "state": None}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = True
        mock_settings.invite_gate = True
        await GateMiddleware()(handler, event, data)

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.call_args.kwargs
    assert "инвайт" in _extract_sent_text(bot.send_message).lower()
    assert_keyboard_has_buttons(kwargs["reply_markup"], ["Ввести инвайт", "Оферта", "Восстановить доступ"])


@pytest.mark.asyncio
async def test_gate_middleware_allows_start_command_when_not_passed() -> None:
    """Invite gate MUST whitelist /start so handler can show gate or free menu."""
    user = MagicMock(spec=User)
    user.passed_gate = False
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=999050, is_bot=False, username="u")
    event.chat = MagicMock(spec=Chat, id=999050)
    event.text = "/start"
    event.successful_payment = None
    bot = AsyncMock()
    data = {"bot": bot, "state": None}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = False
        mock_settings.invite_gate = True
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_gate_middleware_legacy_presentation_flag_allows_gate_invite_callback() -> None:
    """Legacy PRESENTATION_ONLY=true still allows gate:* callbacks."""
    user = MagicMock(spec=User)
    user.passed_gate = False
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=CallbackQuery)
    event.from_user = MagicMock(id=999101, is_bot=False, username="u")
    event.data = Gate(action="invite_enter").pack()
    event.message = MagicMock(spec=Message)
    event.message.chat = MagicMock(spec=Chat, id=999101)
    data = {"bot": AsyncMock(), "state": None}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = True
        mock_settings.invite_gate = True
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)


@pytest.mark.asyncio
async def test_gate_middleware_legacy_presentation_flag_allows_gate_invite_state_message() -> None:
    """GateInvite:* state message must not be blocked (legacy flag irrelevant)."""
    user = MagicMock(spec=User)
    user.passed_gate = False
    _, session_cm = make_session_context(user=user)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=999102, is_bot=False, username="u")
    event.chat = MagicMock(spec=Chat, id=999102)
    event.text = "INVITE-CODE"
    event.successful_payment = None
    bot = AsyncMock()
    state = AsyncMock()
    state.get_state = AsyncMock(return_value="GateInvite:waiting_code")
    data = {"bot": bot, "state": state}
    handler = AsyncMock()

    with patch("app.client_bot.middlewars.gate._sm", session_cm), patch(
        "app.client_bot.middlewars.gate.settings"
    ) as mock_settings:
        mock_settings.presentation_only = True
        mock_settings.invite_gate = True
        await GateMiddleware()(handler, event, data)

    handler.assert_awaited_once_with(event, data)
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_gate_middleware_none_telegram_id_passes_through() -> None:
    """None telegram_id bypasses gate logic."""
    handler = AsyncMock()
    event = MagicMock(spec=Message)
    event.from_user = None
    data = {"bot": AsyncMock()}
    result = await GateMiddleware()(handler, event, data)
    handler.assert_awaited_once_with(event, data)
    assert result is handler.return_value
