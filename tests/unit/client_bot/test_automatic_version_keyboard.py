"""Подменю выбора версии АвтоАпдейтера: вход из меню РК + отдельное сообщение."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.callbacks import (
    AutoUpdaterVersionMenuBack,
    AutoUpdaterVersionMenuOpen,
    AutoUpdaterVersionToggle,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.automatic_version_ui import (
    AUTOMATIC_VERSION_UI_CHOICES,
    FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID,
    FSM_ADV_AUTO_VER_PARENT_MESSAGE_ID,
    automatic_version_main_menu_button,
    build_automatic_version_submenu_markup,
    normalize_automatic_version_ui,
    show_relevant_phrase_toggle,
)


@pytest.mark.unit
def test_fsm_keys_stable_contract() -> None:
    assert FSM_ADV_AUTO_VER_PARENT_MESSAGE_ID == "adv_auto_ver_parent_message_id"
    assert FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID == "adv_auto_ver_menu_adv_setting_id"


@pytest.mark.unit
def test_main_menu_entry_shows_current_version_in_label() -> None:
    adv = MagicMock()
    adv.id = 1
    adv.automatic_version = 3
    btn = automatic_version_main_menu_button(adv)
    assert "V3" in btn.text
    adv.automatic_version = 2
    btn_v2 = automatic_version_main_menu_button(adv)
    assert "V2" in btn_v2.text


@pytest.mark.unit
def test_main_menu_button_opens_submenu_callback() -> None:
    adv = MagicMock()
    adv.id = 42
    adv.automatic_version = 2
    btn = automatic_version_main_menu_button(adv)
    parsed = AutoUpdaterVersionMenuOpen.unpack(btn.callback_data)
    assert parsed.adv_setting_original_id == 42


@pytest.mark.unit
def test_submenu_markup_version_rows_and_back() -> None:
    adv = MagicMock()
    adv.id = 99
    adv.automatic_version = 2
    markup = build_automatic_version_submenu_markup(adv)
    assert len(markup.inline_keyboard) == len(AUTOMATIC_VERSION_UI_CHOICES) + 1
    assert AUTOMATIC_VERSION_UI_CHOICES == (2, 3)
    for i, version in enumerate(AUTOMATIC_VERSION_UI_CHOICES):
        row = markup.inline_keyboard[i]
        assert len(row) == 1
        parsed = AutoUpdaterVersionToggle.unpack(row[0].callback_data)
        assert parsed.new_version == version
        assert parsed.adv_setting_original_id == 99
    back_row = markup.inline_keyboard[-1]
    assert len(back_row) == 1
    assert back_row[0].text == "Назад"
    _ = AutoUpdaterVersionMenuBack.unpack(back_row[0].callback_data)


@pytest.mark.unit
def test_normalize_automatic_version_ui_none_is_two() -> None:
    assert normalize_automatic_version_ui(None) == 2


@pytest.mark.unit
def test_normalize_automatic_version_ui_v1_is_two() -> None:
    assert normalize_automatic_version_ui(1) == 2


@pytest.mark.unit
def test_submenu_shows_v2_checkmark_when_db_still_v1() -> None:
    adv = MagicMock()
    adv.id = 99
    adv.automatic_version = 1
    markup = build_automatic_version_submenu_markup(adv)
    v2_row = markup.inline_keyboard[0][0]
    assert v2_row.text == "✓ Авто V2"


@pytest.mark.unit
def test_show_relevant_phrase_toggle_only_v2_for_now() -> None:
    assert show_relevant_phrase_toggle(2) is True
    assert show_relevant_phrase_toggle(1) is False
    assert show_relevant_phrase_toggle(3) is False
