"""Кнопка входа в отчёт последнего V3-тика в меню настроек РК."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton

from app.client_bot.user_interface.views.callbacks import V3TickReportOpen
from app.modules.common_slaves.wildberries.models import AdvSetting


def v3_tick_report_main_button(adv_setting: AdvSetting) -> InlineKeyboardButton:
    """Кнопка «Последние действия с ключами» (только V3)."""
    return InlineKeyboardButton(
        text="Последние действия с ключами",
        callback_data=V3TickReportOpen(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )
