"""Telegram UI: ``AdvSetting.aggressiveness`` (1–3), только при Авто V3."""

from __future__ import annotations

from typing import Final

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.user_interface.views.callbacks import (
    V3RolloutAggMenuBack,
    V3RolloutAggMenuOpen,
    V3RolloutAggSet,
)
from app.modules.common_slaves.wildberries.models import AdvSetting

_LEVEL_LABELS: Final[dict[int, str]] = {
    1: "Минимальная (сначала слой MIN_CPM)",
    2: "Средняя",
    3: "Максимальная (по умолчанию)",
}

def v3_aggressiveness_letter(level: int) -> str:
    """Краткий уровень агрессивности V3 (цифра 1–3) для кнопки меню настроек РК."""
    return str(level)


def v3_aggressiveness_level(level: int) -> str:
    """Синоним :func:`v3_aggressiveness_letter` для подписей в UI."""
    return v3_aggressiveness_letter(level)


def v3_aggressiveness_caption(level: int) -> str:
    """Уровень и расшифровка для страницы настроек РК."""
    label = _LEVEL_LABELS.get(level, str(level))
    return f"{v3_aggressiveness_letter(level)} — {label}"

FSM_V3_ROLLOUT_PARENT_MESSAGE_ID = "v3_rollout_parent_message_id"
FSM_V3_ROLLOUT_MENU_ADV_SETTING_ID = "v3_rollout_menu_adv_setting_id"


def v3_rollout_aggressiveness_main_button(adv_setting: AdvSetting) -> InlineKeyboardButton:
    cur = int(adv_setting.aggressiveness)
    return InlineKeyboardButton(
        text=f"V3 агр.: {v3_aggressiveness_letter(cur)}",
        callback_data=V3RolloutAggMenuOpen(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )


def build_v3_rollout_submenu_markup(adv_setting: AdvSetting) -> InlineKeyboardMarkup:
    current = int(adv_setting.aggressiveness)
    rows: list[list[InlineKeyboardButton]] = []
    for level in (1, 2, 3):
        text = (
            f"✓ {_LEVEL_LABELS[level]}"
            if level == current
            else f"{level}. {_LEVEL_LABELS[level]}"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=V3RolloutAggSet(
                        adv_setting_original_id=adv_setting.id,
                        level=level,
                    ).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=V3RolloutAggMenuBack().pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


_SUBMENU_INTRO = (
    "Агрессивность раскрутки V3 (1–3) действует только вне полочной фазы "
    "(режим полок выключен или авто-кампания не в статусе «запущена»).\n"
    "Когда полки включены и авто запущена — используется логика полок, как во v2.\n\n"
    "За один цикл — одно переключение режима ключа; вверх — сначала ключи с выше конверсией, "
    "вниз при экономии — сначала более дорогие по CPA.\n\n"
    "Выберите уровень:"
)


def v3_rollout_submenu_caption() -> str:
    return _SUBMENU_INTRO
