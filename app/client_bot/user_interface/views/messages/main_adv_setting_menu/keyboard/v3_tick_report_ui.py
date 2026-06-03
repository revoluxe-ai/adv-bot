"""Кнопки экрана отчёта последнего V3-тика."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.user_interface.views.callbacks import (
    V3TickReportBack,
    V3TickReportRefresh,
)

FSM_V3_TICK_REPORT_PARENT_MESSAGE_ID = "v3_tick_report_parent_message_id"
FSM_V3_TICK_REPORT_ADV_SETTING_ID = "v3_tick_report_adv_setting_id"


def build_v3_tick_report_keyboard(adv_setting_original_id: int) -> InlineKeyboardMarkup:
    """Клавиатура: новый отчёт из Redis + назад к меню РК."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data=V3TickReportRefresh(
                        adv_setting_original_id=adv_setting_original_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀ Назад к меню РК",
                    callback_data=V3TickReportBack().pack(),
                )
            ],
        ]
    )
