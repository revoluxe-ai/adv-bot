"""Unit tests for admin panel gate and user-access reset handlers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers.admin_panel import (
    admin_reset_user_access_process,
    show_admin_panel,
)


def make_session_context(*, user: object | None) -> tuple[AsyncMock, AsyncGenerator[AsyncSession, None]]:
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
async def test_show_admin_panel_contains_reset_user_button() -> None:
    """Menu edit runs only when callback.message is a Message (not InaccessibleMessage)."""
    callback = MagicMock()
    # bare MagicMock fails isinstance(..., Message); show_admin_panel then skips edit_text.
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    await show_admin_panel(callback, state)

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    keyboard = callback.message.edit_text.await_args.kwargs["reply_markup"]
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "♻️ Сбросить пользователя" in texts


@pytest.mark.asyncio
async def test_admin_reset_user_access_process_resets_db_and_subscription_cache() -> None:
    user = MagicMock()
    user.id = 12
    user.username = "target_user"
    user.passed_gate = True
    user.phone = "+79990001122"
    session, session_cm = make_session_context(user=user)

    message = MagicMock(spec=Message)
    message.text = "123456789"
    message.chat = MagicMock(spec=Chat, id=500)
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    redis_client = MagicMock()
    redis_client.delete = AsyncMock(return_value=1)

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel._sm",
        session_cm,
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel.AppContainer"
    ) as app_container_cls:
        app_container_cls.return_value.redis_client_wrapper.return_value = redis_client
        await admin_reset_user_access_process(message, state)

    session.commit.assert_awaited_once()
    redis_client.delete.assert_awaited_once_with(
        "client_bot:support_channel_subscription:123456789"
    )
    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    answer_text = message.answer.await_args.args[0]
    assert "сброшен" in answer_text.lower()
    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    texts = [button.text for row in reply_markup.inline_keyboard for button in row]
    assert "♻️ Сбросить пользователя" in texts
