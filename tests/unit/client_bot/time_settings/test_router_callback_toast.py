"""Регрессия: toast time_settings после pre-answer middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.utils.callback_answer import CallbackAnswer

from app.client_bot.user_interface.handlers.time_settings.router import _redraw


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_sets_callback_toast_with_alert() -> None:
    """Симптом: validation/save alert не доходил до пользователя после pre=True."""
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    session = MagicMock()
    callback_answer = CallbackAnswer(answered=False, text="Запрос в обработке")

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
            callback_answer=callback_answer,
            alert="End должен быть больше Start",
        )

    assert callback_answer.text == "End должен быть больше Start"
    assert callback_answer.show_alert is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_silent_toast_when_message_changed_without_alert() -> None:
    """Успешный edit — пустой toast, без «Без изменений»."""
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    session = MagicMock()
    callback_answer = CallbackAnswer(answered=False, text="Запрос в обработке")

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
        await _redraw(
            callback,
            only_markup=False,
            callback_answer=callback_answer,
            alert=None,
        )

    assert callback_answer.text == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_shows_no_changes_when_edit_unchanged_without_alert() -> None:
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    session = MagicMock()
    callback_answer = CallbackAnswer(answered=False, text="Запрос в обработке")

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
        await _redraw(
            callback,
            only_markup=True,
            callback_answer=callback_answer,
            alert=None,
        )

    assert callback_answer.text == "Без изменений"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redraw_stale_session_toast() -> None:
    callback = AsyncMock()
    callback.message.message_id = 42
    callback.from_user.id = 1

    callback_answer = CallbackAnswer(answered=False, text="Запрос в обработке")

    with patch(
        "app.client_bot.user_interface.handlers.time_settings.router.find_session_by_message",
        return_value=None,
    ):
        await _redraw(
            callback,
            only_markup=False,
            callback_answer=callback_answer,
            alert=None,
        )

    assert callback_answer.text == "Откройте актуальное меню"
