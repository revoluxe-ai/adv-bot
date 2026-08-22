"""Unit tests for paid auto-management landing copy and keyboard wiring."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.auto_management_landing import (
    AutoManagementHowItWorks,
    AutoManagementLanding,
)
from tests.helpers.telegram_message_asserts import (
    assert_html_is_telegram_safe,
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    extract_button_texts,
)


def _wb_user_cabinet() -> SimpleNamespace:
    return SimpleNamespace(id=55, wb_cabinet_id=155)


def _adv_setting(*, bot_active: bool) -> SimpleNamespace:
    return SimpleNamespace(id=77, bot_active=bot_active)


@pytest.mark.unit
def test_landing_text_contains_required_paid_copy() -> None:
    landing = AutoManagementLanding(
        bot=SimpleNamespace(),
        chat_id=100,
        wb_user_cabinet=_wb_user_cabinet(),
        adv_setting=_adv_setting(bot_active=False),
    )

    text = landing.text

    assert_message_within_telegram_limit(text)
    assert_html_is_telegram_safe(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Бесплатный режим",
            "Платный режим",
            "автоуправление",
            "токен с возможностью изменений",
            "баланс",
        ],
    )


@pytest.mark.unit
def test_landing_keyboard_for_disabled_campaign_contains_enable_balance_help_and_back() -> None:
    landing = AutoManagementLanding(
        bot=SimpleNamespace(),
        chat_id=100,
        wb_user_cabinet=_wb_user_cabinet(),
        adv_setting=_adv_setting(bot_active=False),
    )

    keyboard = landing.keyboard
    texts = extract_button_texts(keyboard)

    assert_keyboard_has_buttons(
        keyboard,
        [
            "✅ Включить автоуправление",
            "💳 Пополнить баланс",
            "❓ Как работает автоуправление",
            "⬅️ Назад",
        ],
    )
    assert "⏸ Полностью отключить бот от управления РК" not in texts
    assert keyboard.inline_keyboard[0][0].callback_data == callbacks.TurnBot(
        action="on",
        adv_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()
    assert keyboard.inline_keyboard[1][0].callback_data == callbacks.AddBalance(
        wb_cabinet_original_id=155
    ).pack()


@pytest.mark.unit
def test_landing_keyboard_for_enabled_campaign_contains_disable_button() -> None:
    landing = AutoManagementLanding(
        bot=SimpleNamespace(),
        chat_id=100,
        wb_user_cabinet=_wb_user_cabinet(),
        adv_setting=_adv_setting(bot_active=True),
    )

    keyboard = landing.keyboard
    texts = extract_button_texts(keyboard)

    assert "⏸ Полностью отключить бот от управления РК" in texts
    assert "✅ Включить автоуправление" not in texts
    assert keyboard.inline_keyboard[0][0].callback_data == callbacks.TurnBot(
        action="off",
        adv_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()


@pytest.mark.unit
def test_how_it_works_text_and_back_button_are_present() -> None:
    screen = AutoManagementHowItWorks(
        bot=SimpleNamespace(),
        chat_id=100,
        wb_user_cabinet=_wb_user_cabinet(),
        adv_setting=_adv_setting(bot_active=False),
    )

    text = screen.text
    keyboard = screen.keyboard

    assert_message_within_telegram_limit(text)
    assert_html_is_telegram_safe(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Бесплатный режим",
            "Платный режим",
            "бот сам ведёт рекламу",
            "токен с возможностью изменений",
            "баланс",
        ],
    )
    assert_keyboard_has_buttons(keyboard, ["⬅️ Назад"])
    assert keyboard.inline_keyboard[0][0].callback_data == callbacks.AutoManagementLanding(
        action="open",
        adv_setting_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()


@pytest.mark.unit
def test_no_dead_end_in_campaign_menu_to_landing_to_how_it_works_back_flow() -> None:
    landing = AutoManagementLanding(
        bot=SimpleNamespace(),
        chat_id=100,
        wb_user_cabinet=_wb_user_cabinet(),
        adv_setting=_adv_setting(bot_active=False),
    )
    how_it_works = AutoManagementHowItWorks(
        bot=SimpleNamespace(),
        chat_id=100,
        wb_user_cabinet=_wb_user_cabinet(),
        adv_setting=_adv_setting(bot_active=False),
    )

    landing_open_from_campaign = callbacks.AutoManagementLanding(
        action="open",
        adv_setting_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()
    how_it_works_from_landing = callbacks.AutoManagementLanding(
        action="how",
        adv_setting_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()
    back_to_landing = callbacks.AutoManagementLanding(
        action="open",
        adv_setting_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()
    back_to_campaign_menu = callbacks.AutoManagementLanding(
        action="back",
        adv_setting_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()

    assert landing_open_from_campaign == callbacks.AutoManagementLanding(
        action="open",
        adv_setting_original_id=77,
        wb_user_cabinet_original_id=55,
    ).pack()
    assert landing.keyboard.inline_keyboard[2][0].callback_data == how_it_works_from_landing
    assert how_it_works.keyboard.inline_keyboard[0][0].callback_data == back_to_landing
    assert landing.keyboard.inline_keyboard[3][0].callback_data == back_to_campaign_menu
