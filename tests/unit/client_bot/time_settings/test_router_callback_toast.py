"""Регрессия: пояснения time_settings в чат после pre-answer на Dispatcher."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.time_settings.router import (
    _STALE_MENU_TOAST,
    _redraw,
    time_settings_callback,
)
from app.client_bot.user_interface.handlers.time_settings.callbacks import TS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_sends_alert_to_chat() -> None:
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    session = MagicMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
            return_value=session,
        ),
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router.render_screen",
            return_value=("screen", MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router._edit_message_content",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        await _redraw(
            callback,
            only_markup=False,
            alert="End должен быть больше Start",
        )

    callback.message.answer.assert_awaited_once_with("End должен быть больше Start")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_silent_when_message_changed_without_alert() -> None:
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    session = MagicMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
            return_value=session,
        ),
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router.render_screen",
            return_value=("screen", MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router._edit_message_content",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await _redraw(callback, only_markup=False, alert=None)

    callback.message.answer.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_shows_no_changes_when_edit_unchanged_without_alert() -> None:
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    session = MagicMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
            return_value=session,
        ),
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router.render_screen",
            return_value=("screen", MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.time_settings.router._safe_edit_reply_markup",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        await _redraw(callback, only_markup=True, alert=None)

    callback.message.answer.assert_awaited_once_with("Без изменений")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_stale_session_message() -> None:
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    with patch(
        "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
        return_value=None,
    ):
        await _redraw(callback, only_markup=False, alert=None)

    callback.message.answer.assert_awaited_once_with(_STALE_MENU_TOAST)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_stale_session_id_sends_message() -> None:
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.message_id = 42

    session = MagicMock()
    session.session_id = "current"

    callback_data = TS(a="to_week", sid="stale")

    with patch(
        "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
        return_value=session,
    ):
        await time_settings_callback(
            callback=callback,
            callback_data=callback_data,
        )

    callback.message.answer.assert_awaited_once_with(_STALE_MENU_TOAST)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_noop_does_not_spam_chat() -> None:
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.message_id = 42

    session = MagicMock()
    session.session_id = "s1"
    session.state = MagicMock()

    callback_data = TS(a="noop", sid="s1")

    with patch(
        "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
        return_value=session,
    ):
        await time_settings_callback(
            callback=callback,
            callback_data=callback_data,
        )

    callback.message.answer.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_done_sends_demo_message() -> None:
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.message_id = 42

    session = MagicMock()
    session.session_id = "s1"
    session.state = MagicMock()

    callback_data = TS(a="done", sid="s1")

    with patch(
        "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
        return_value=session,
    ):
        await time_settings_callback(
            callback=callback,
            callback_data=callback_data,
        )

    callback.message.answer.assert_awaited_once_with("Настройки применены (демо)")
