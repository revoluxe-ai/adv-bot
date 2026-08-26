"""UI для выбора `AdvSetting.automatic_version`: вход из меню РК + отдельное подменю."""

from __future__ import annotations

from typing import Final

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.user_interface.views.callbacks import (
    AutoUpdaterVersionMenuBack,
    AutoUpdaterVersionMenuOpen,
    AutoUpdaterVersionToggle,
)
from app.modules.common_slaves.wildberries.models import AdvSetting

# Версии, отображаемые в подменю (отдельная кнопка на каждую).
AUTOMATIC_VERSION_UI_CHOICES: Final[tuple[int, ...]] = (2, 3)

# FSM: главное меню РК (фото + клавиатура) при открытии подменю — для sync кнопки «сейчас V…».
FSM_ADV_AUTO_VER_PARENT_MESSAGE_ID = "adv_auto_ver_parent_message_id"
FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID = "adv_auto_ver_menu_adv_setting_id"


def normalize_automatic_version_ui(raw: int | None) -> int:
    """None и deprecated V1 в БД отображаем как продуктовый дефолт (2)."""
    if raw is None or raw == 1:
        return 2
    return raw


def show_relevant_phrase_toggle(version: int) -> bool:
    """Показывать ли кнопку «только релевантные фразы». Пока только V2 (V3 — отдельно по продукту)."""
    # TODO: Убрать вообще эту проверку

    return True

# TODO: Remove this alias after the show_if rename is complete Убрать костыль 
# Alias для существующих импортов/тестов после промежуточного rename show_if.
show_if = show_relevant_phrase_toggle


def automatic_version_main_menu_button(adv_setting: AdvSetting) -> InlineKeyboardButton:
    """Одна кнопка входа в подменю выбора версии."""
    current = normalize_automatic_version_ui(adv_setting.automatic_version)
    return InlineKeyboardButton(
        text=f"Версия АвтоАпдейтера (сейчас V{current})",
        callback_data=AutoUpdaterVersionMenuOpen(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )


def build_automatic_version_submenu_markup(adv_setting: AdvSetting) -> InlineKeyboardMarkup:
    """Подменю: по одной кнопке на версию + «Назад»."""
    current = normalize_automatic_version_ui(adv_setting.automatic_version)
    rows: list[list[InlineKeyboardButton]] = []
    for version in AUTOMATIC_VERSION_UI_CHOICES:
        text = f"✓ Авто V{version}" if version == current else f"Авто V{version}"
        cb = AutoUpdaterVersionToggle(
            new_version=version,
            adv_setting_original_id=adv_setting.id,
        ).pack()
        rows.append([InlineKeyboardButton(text=text, callback_data=cb)])
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AutoUpdaterVersionMenuBack().pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
