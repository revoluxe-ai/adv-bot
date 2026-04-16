"""Unit tests for MainMenu and get_main_menu_keyboard."""

from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.handlers.shop_choice_message import (
    MainMenu,
    get_main_menu_keyboard,
)
from app.client_bot.user_interface.views.get_main_text import get_main_text
from app.client_bot.user_interface.views import callbacks
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel


def test_main_menu_text_contains_key_phrases() -> None:
    """MainMenu.text returns text from get_main_text, contains key phrases."""
    menu = MainMenu(bot=None, chat_id=12345, full_client_ui=True)  # type: ignore[arg-type]
    text = menu.text
    assert "Экономическое управление" in text
    assert "Wildberries" in text


@patch("app.client_bot.user_interface.views.get_main_text.settings")
def test_minimal_main_text_without_invite_requirement(mock_settings) -> None:
    mock_settings.presentation_only = True
    text = get_main_text(123456, full_client_ui=False)
    assert "Записаться на презентацию" in text
    assert "инвайт" not in text.lower()


@patch("app.client_bot.user_interface.views.get_main_text.settings")
def test_minimal_main_text_when_already_booked(mock_settings) -> None:
    mock_settings.presentation_only = True
    text = get_main_text(
        123456,
        full_client_ui=False,
        booked_slot_human="пт, 10.04 16:00-16:40 МСК",
    )
    assert "Вы записаны на презентацию" in text
    assert "пт, 10.04 16:00-16:40 МСК" in text
    assert "связаться с менеджером" in text.lower()


def test_get_main_menu_keyboard_regular_user_three_buttons() -> None:
    """Обычный пользователь: Мои магазины, Мой баланс, Показать инвайт."""
    user_id = 999999  # Not in ADMINS
    kb = get_main_menu_keyboard(user_id, full_client_ui=True)
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert rows[0][0].text == "Мои магазины"
    assert rows[0][0].callback_data == callbacks.ShowShopsList().pack()
    assert rows[1][0].text == "Мой баланс"
    assert rows[1][0].callback_data == callbacks.UserBalanceMenu().pack()
    assert rows[2][0].text == "Показать инвайт"
    assert rows[2][0].callback_data == callbacks.InviteShow().pack()


def test_get_main_menu_keyboard_not_passed_gate_has_booking_button() -> None:
    """Минимальное меню на входе: кнопка записи на презентацию."""
    kb = get_main_menu_keyboard(user_telegram_id=999999, full_client_ui=False)
    rows = kb.inline_keyboard
    assert len(rows) == 1
    assert rows[0][0].text == "Записаться на презентацию"
    assert (
        rows[0][0].callback_data
        == callbacks.PresentationBooking(action="menu").pack()
    )


def test_get_main_menu_keyboard_booked_only_contact_manager_url() -> None:
    kb = get_main_menu_keyboard(
        user_telegram_id=999999,
        full_client_ui=False,
        booked_slot_human="пт, 10.04 16:00-16:40 МСК",
    )
    rows = kb.inline_keyboard
    assert len(rows) == 1
    assert rows[0][0].text == "Связаться с менеджером"
    assert rows[0][0].url is not None
    assert "t.me/" in rows[0][0].url


def test_get_main_menu_keyboard_invite_visible_when_invite_gate_off() -> None:
    """INVITE_GATE=false не скрывает кнопку «Показать инвайт» на полном меню."""
    kb = get_main_menu_keyboard(999999, full_client_ui=True)
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert rows[2][0].text == "Показать инвайт"


@patch("app.client_bot.admin_access.ADMINS", [123])
def test_get_main_menu_keyboard_admin_four_buttons() -> None:
    """Админ: Панель, Мои магазины, Мой баланс, Показать инвайт."""
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
    """MainMenu(bot, chat_id)() calls bot.send_message with text, reply_markup, parse_mode=HTML."""
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
