"""Unit tests for the campaign minus-phrase settings screen."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.client_bot.user_interface.views.messages.main_adv_setting_menu.minus_phrases_setting import (
    MinusPhrasesSettingScreen,
)
from tests.helpers.telegram_message_asserts import (
    assert_html_is_telegram_safe,
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


def _screen(*, enabled: bool) -> MinusPhrasesSettingScreen:
    return MinusPhrasesSettingScreen(
        bot=SimpleNamespace(),
        chat_id=101,
        wb_user_cabinet=SimpleNamespace(id=55),
        adv_setting=SimpleNamespace(
            id=77,
            auto_update_minus_phrases=enabled,
        ),
    )


@pytest.mark.unit
def test_minus_phrases_setting_screen_disabled_copy_is_safe() -> None:
    screen = _screen(enabled=False)

    assert_message_within_telegram_limit(screen.text)
    assert_html_is_telegram_safe(screen.text)
    assert_message_contains_required_phrases(
        screen.text,
        [
            "Обновление минус-фраз выключено",
            "Эта настройка управляет",
            "обновлением минус-фраз в кабинете WB",
            "бот может менять минус-фразы",
            "по умолчанию она выключена для безопасного старта",
            "включить данную функцию",
        ],
    )
    assert_no_raw_technical_text(screen.text)
    assert_keyboard_has_buttons(
        screen.keyboard,
        [
            "✅ Включить обновление минус-фраз",
            "⬅️ Назад",
        ],
    )


@pytest.mark.unit
def test_minus_phrases_setting_screen_enabled_has_pause_button() -> None:
    screen = _screen(enabled=True)

    assert_message_contains_required_phrases(
        screen.text,
        ["Обновление минус-фраз включено"],
    )
    assert_keyboard_has_buttons(
        screen.keyboard,
        [
            "⏸ Выключить обновление минус-фраз",
            "⬅️ Назад",
        ],
    )
