"""Unit tests for start_registration: new user (no record in DB) and existing user."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message, User as TelegramUser

from app.client_bot.user_interface.handlers.start_registration_func import start_registration
from app.client_bot.user_interface.views.gate import get_gate_message_text


@pytest.mark.asyncio
async def test_start_registration_new_user_creates_user_and_shows_gate() -> None:
    """When user does not exist in DB, create_user is called and gate screen is shown; MainMenu is not called."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    telegram_id = 70001
    chat_id = 70001
    message = MagicMock(spec=Message)
    message.text = "/start"
    message.chat = MagicMock(spec=Chat, id=chat_id)
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = telegram_id
    message.from_user.username = "new_user_70001"

    # Session: execute returns result where unique().scalar_one_or_none() -> None (no user)
    result_mock = MagicMock()
    result_mock.unique.return_value.scalar_one_or_none.return_value = None
    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=result_mock)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_mock)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    mock_user = MagicMock()
    mock_user.passed_gate = False

    with patch(
        "app.client_bot.user_interface.handlers.start_registration_func.sm"
    ) as mock_sm, patch(
        "app.client_bot.user_interface.handlers.start_registration_func.create_user",
        new_callable=AsyncMock,
        return_value=mock_user,
    ) as mock_create_user, patch(
        "app.client_bot.user_interface.handlers.start_registration_func.MainMenu"
    ) as mock_main_menu, patch(
        "app.client_bot.user_interface.handlers.start_registration_func.settings"
    ) as mock_settings:
        mock_settings.invite_gate = True
        mock_sm.return_value = session_cm

        await start_registration(message, bot, state)

        mock_create_user.assert_awaited_once()
        call_kw = mock_create_user.call_args
        assert call_kw[0][1] == telegram_id
        assert call_kw[1]["username"] == "new_user_70001"
        assert call_kw[1]["adv_updater_user_chat_id"] == chat_id

        bot.send_message.assert_awaited_once()
        send_args, send_kw = bot.send_message.call_args
        assert send_args[0] == chat_id
        assert get_gate_message_text() in (send_args[1] if len(send_args) > 1 else send_kw.get("text", ""))
        assert send_kw.get("reply_markup") is not None

        mock_main_menu.assert_not_called()
