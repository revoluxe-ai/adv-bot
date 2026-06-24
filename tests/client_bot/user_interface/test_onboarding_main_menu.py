"""Unit tests for MainMenu and get_main_menu_keyboard."""

from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.handlers.shop_choice_message import (
    MainMenu,
    get_main_menu_keyboard,
)
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import Gate
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel


def test_main_menu_text_contains_key_phrases() -> None:
    """MainMenu.text returns text from get_main_text, contains key phrases."""
    menu = MainMenu(bot=None, chat_id=12345, full_client_ui=True)  # type: ignore[arg-type]
    text = menu.text
    assert "Экономическое управление" in text
    assert "Wildberries" in text


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_main_menu_text_presentation_only_invite_copy(mock_settings) -> None:
    """presentation_only main text should prompt invite-based free access."""
    mock_settings.presentation_only = True
    menu = MainMenu(bot=None, chat_id=12345, full_client_ui=False)  # type: ignore[arg-type]
    text = menu.text
    assert "Ваш Telegram ID" in text
    assert "Введите инвайт" in text
    assert "бесплатный доступ" in text


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_main_menu_keyboard_regular_user_three_buttons(mock_settings) -> None:
    """Regular user sees shops, balance, and invite buttons."""
    mock_settings.presentation_only = False
    mock_settings.invite_gate = True
    user_id = 999999
    kb = get_main_menu_keyboard(user_id, full_client_ui=True)
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert rows[0][0].text == "Мои магазины"
    assert rows[0][0].callback_data == callbacks.ShowShopsList().pack()
    assert rows[1][0].text == "Мой баланс"
    assert rows[1][0].callback_data == callbacks.UserBalanceMenu().pack()
    assert rows[2][0].text == "Показать инвайт"
    assert rows[2][0].callback_data == callbacks.InviteShow().pack()


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_main_menu_keyboard_invite_visible_when_invite_gate_off(mock_settings) -> None:
    """INVITE_GATE=false does not hide the invite button in the full menu."""
    mock_settings.presentation_only = False
    mock_settings.invite_gate = False
    kb = get_main_menu_keyboard(999999, full_client_ui=True)
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert rows[2][0].text == "Показать инвайт"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
@patch("app.client_bot.admin_access.const.ADMINS", [123])
def test_get_main_menu_keyboard_admin_four_buttons(mock_settings) -> None:
    """Admin sees panel, shops, balance, and invite buttons."""
    mock_settings.presentation_only = False
    mock_settings.invite_gate = True
    user_id = 123
    kb = get_main_menu_keyboard(user_id, full_client_ui=True)
    rows = kb.inline_keyboard
    assert len(rows) == 4
    assert rows[0][0].text == "Панель администратора"
    assert rows[0][0].callback_data == AdminPanel(action="menu").pack()
    assert rows[1][0].text == "Мои магазины"
    assert rows[2][0].text == "Мой баланс"
    assert rows[3][0].text == "Показать инвайт"


@pytest.mark.asyncio
async def test_main_menu_calls_bot_send_message() -> None:
    """MainMenu(bot, chat_id)() calls bot.send_message with text and keyboard."""
    bot = AsyncMock()
    chat_id = 12345
    menu = MainMenu(bot, chat_id, full_client_ui=True)
    await menu()
    bot.send_message.assert_awaited_once()
    call_kw = bot.send_message.call_args[1]
    assert call_kw["chat_id"] == chat_id
    assert "Экономическое управление" in call_kw["text"]
    assert "Wildberries" in call_kw["text"]
    assert call_kw["reply_markup"] is not None
    assert call_kw["parse_mode"] == "HTML"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_main_menu_keyboard_presentation_only_shows_invite_entry(mock_settings) -> None:
    """presentation_only minimal menu should open direct invite entry."""
    mock_settings.presentation_only = True
    kb = get_main_menu_keyboard(999999, full_client_ui=False)
    rows = kb.inline_keyboard
    assert len(rows) == 1
    assert rows[0][0].text == "Ввести инвайт"
    assert rows[0][0].callback_data == Gate(action="invite_enter").pack()
