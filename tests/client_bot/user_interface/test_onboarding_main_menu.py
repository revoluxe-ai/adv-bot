"""Unit tests for MainMenu and onboarding keyboards."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.handlers.shop_choice_message import (
    MainMenu,
    get_main_menu_keyboard,
)
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import Gate
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel
from tests.helpers.telegram_message_asserts import (
    assert_html_is_telegram_safe,
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


def test_main_menu_text_contains_key_phrases() -> None:
    """MainMenu.text returns user-facing onboarding copy."""
    menu = MainMenu(bot=None, chat_id=12345, full_client_ui=True)  # type: ignore[arg-type]
    text = menu.text
    assert_message_within_telegram_limit(text)
    assert_html_is_telegram_safe(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Telegram ID",
            "Wildberries",
            "Начните с раздела",
            "Мои магазины",
            "подключите токен",
            "выберите рекламную кампанию",
        ],
    )
    assert "Экономическое управление" in text
    assert_no_raw_technical_text(text)




@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_main_menu_keyboard_regular_user_three_buttons(mock_settings) -> None:
    """Regular user sees shops, balance, and invite buttons."""
    mock_settings.presentation_only = False
    mock_settings.invite_gate = True
    kb = get_main_menu_keyboard(999999, full_client_ui=True)
    assert_keyboard_has_buttons(kb, ["Мои магазины", "Мой баланс", "Показать инвайт"])
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert rows[0][0].callback_data == callbacks.ShowShopsList().pack()
    assert rows[1][0].callback_data == callbacks.UserBalanceMenu().pack()
    assert rows[2][0].callback_data == callbacks.InviteShow().pack()


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_main_menu_keyboard_invite_visible_when_invite_gate_off(mock_settings) -> None:
    """INVITE_GATE=false does not hide the invite button in the full menu."""
    mock_settings.presentation_only = False
    mock_settings.invite_gate = False
    kb = get_main_menu_keyboard(999999, full_client_ui=True)
    assert_keyboard_has_buttons(kb, ["Показать инвайт"])
    assert len(kb.inline_keyboard) == 3


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
@patch("app.client_bot.admin_access.const.ADMINS", [123])
def test_get_main_menu_keyboard_admin_four_buttons(mock_settings) -> None:
    """Admin sees panel, shops, balance, and invite buttons."""
    mock_settings.presentation_only = False
    mock_settings.invite_gate = True
    kb = get_main_menu_keyboard(123, full_client_ui=True)
    assert_keyboard_has_buttons(
        kb,
        ["Панель администратора", "Мои магазины", "Мой баланс", "Показать инвайт"],
    )
    rows = kb.inline_keyboard
    assert len(rows) == 4
    assert rows[0][0].callback_data == AdminPanel(action="menu").pack()


@pytest.mark.asyncio
async def test_main_menu_calls_bot_send_message() -> None:
    """MainMenu(bot, chat_id)() calls bot.send_message with HTML text and keyboard."""
    bot = AsyncMock()
    menu = MainMenu(bot, 12345, full_client_ui=True)
    await menu()
    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.call_args.kwargs
    text = kwargs["text"]
    assert_message_within_telegram_limit(text)
    assert_html_is_telegram_safe(text)
    assert_message_contains_required_phrases(
        text,
        ["Telegram ID", "Wildberries", "Начните с раздела", "Мои магазины"],
    )
    assert kwargs["reply_markup"] is not None
    assert kwargs["parse_mode"] == "HTML"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_main_menu_keyboard_presentation_only_shows_invite_entry(mock_settings) -> None:
    """presentation_only minimal menu should open direct invite entry."""
    mock_settings.presentation_only = True
    kb = get_main_menu_keyboard(999999, full_client_ui=False)
    assert_keyboard_has_buttons(kb, ["Ввести инвайт"])
    rows = kb.inline_keyboard
    assert len(rows) == 1
    assert rows[0][0].callback_data == Gate(action="invite_enter").pack()
