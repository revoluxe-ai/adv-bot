"""Unit tests for mandatory phone collection middleware and handlers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.middlewars.phone_required import PhoneRequiredMiddleware
from app.client_bot.user_interface.handlers.phone_collection import save_user_phone
from app.utils.db.models import User


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

    with patch(
        "app.client_bot.middlewars.phone_required._sm",
        session_cm,
    ), patch("app.client_bot.middlewars.phone_required.settings") as mock_settings:
        mock_settings.invite_gate = True
        middleware = PhoneRequiredMiddleware()
        await middleware(handler, event, {"bot": bot})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.call_args
    keyboard = kwargs["reply_markup"]
    assert keyboard.keyboard[0][0].request_contact is True


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

    with patch(
        "app.client_bot.middlewars.phone_required._sm",
        session_cm,
    ), patch("app.client_bot.middlewars.phone_required.settings") as mock_settings:
        mock_settings.invite_gate = True
        middleware = PhoneRequiredMiddleware()
        await middleware(handler, event, {"bot": bot})

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

    with patch(
        "app.client_bot.middlewars.phone_required._sm",
        session_cm,
    ), patch("app.client_bot.middlewars.phone_required.settings") as mock_settings:
        mock_settings.invite_gate = True
        middleware = PhoneRequiredMiddleware()
        await middleware(handler, event, {"bot": bot})

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
    event.from_user = MagicMock(id=444, username="u")
    event.message = MagicMock(spec=Message)
    event.message.chat = MagicMock(spec=Chat, id=444)
    bot = AsyncMock()
    handler = AsyncMock()

    with patch(
        "app.client_bot.middlewars.phone_required._sm",
        session_cm,
    ), patch("app.client_bot.middlewars.phone_required.settings") as mock_settings:
        mock_settings.invite_gate = True
        middleware = PhoneRequiredMiddleware()
        await middleware(handler, event, {"bot": bot})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()


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
    bot = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.phone_collection._sm",
        session_cm,
    ):
        await save_user_phone(message, bot)

    assert user.phone == "+79990001122"
    session.commit.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.call_args
    assert kwargs["reply_markup"].remove_keyboard is True


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

    with patch(
        "app.client_bot.user_interface.handlers.phone_collection._sm",
        session_cm,
    ):
        await save_user_phone(message, bot)

    session.commit.assert_not_awaited()
    bot.send_message.assert_awaited_once()
