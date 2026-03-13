"""Unit tests for MainMenu and get_main_menu_keyboard."""

from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.handlers.shop_choice_message import (
    MainMenu,
    get_main_menu_keyboard,
)
from app.client_bot.user_interface.views import callbacks
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel


def test_main_menu_text_contains_key_phrases() -> None:
    """MainMenu.text returns text from get_main_text, contains key phrases."""
    menu = MainMenu(bot=None, chat_id=12345)  # type: ignore[arg-type]
    text = menu.text
    assert "Экономическое управление" in text
    assert "Wildberries" in text


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_main_menu_keyboard_regular_user_three_buttons(mock_settings) -> None:
    """For regular user: 3 buttons (Мои магазины, Мой баланс, Показать инвайт), no admin."""
    mock_settings.invite_gate = True
    user_id = 999999  # Not in ADMINS
    kb = get_main_menu_keyboard(user_id)
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert rows[0][0].text == "Мои магазины"
    assert rows[0][0].callback_data == callbacks.ShowShopsList().pack()
    assert rows[1][0].text == "Мой баланс"
    assert rows[1][0].callback_data == callbacks.UserBalanceMenu().pack()
    assert rows[2][0].text == "Показать инвайт"
    assert rows[2][0].callback_data == callbacks.InviteShow().pack()


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
@patch("app.client_bot.user_interface.handlers.shop_choice_message.const.ADMINS", [123])
def test_get_main_menu_keyboard_admin_four_buttons(mock_settings) -> None:
    """For admin: 4 buttons, first is Панель администратора with AdminPanel(action='menu')."""
    mock_settings.invite_gate = True
    user_id = 123
    kb = get_main_menu_keyboard(user_id)
    rows = kb.inline_keyboard
    assert len(rows) == 4
    assert rows[0][0].text == "Панель администратора"
    assert rows[0][0].callback_data == AdminPanel(action="menu").pack()
    assert rows[1][0].text == "Мои магазины"
    assert rows[2][0].text == "Мой баланс"
    assert rows[3][0].text == "Показать инвайт"


@pytest.mark.asyncio
async def test_main_menu_calls_bot_send_message() -> None:
    """MainMenu(bot, chat_id)() calls bot.send_message with text, reply_markup, parse_mode=HTML."""
    bot = AsyncMock()
    chat_id = 12345
    menu = MainMenu(bot, chat_id)
    await menu()
    bot.send_message.assert_awaited_once()
    call_kw = bot.send_message.call_args[1]
    assert call_kw["chat_id"] == chat_id
    assert "Экономическое управление" in call_kw["text"]
    assert "Wildberries" in call_kw["text"]
    assert call_kw["reply_markup"] is not None
    assert call_kw["parse_mode"] == "HTML"
