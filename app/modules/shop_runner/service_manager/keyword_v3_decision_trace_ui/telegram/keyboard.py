"""Клавиатура экрана «Почему бот так решил?»."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views.callbacks import (
    KeywordV3DecisionTraceBack,
    KeywordV3DecisionTraceRefresh,
)


def build_keyword_v3_decision_trace_keyboard(
    keyword_setting_original_id: int,
    page: int,
    *,
    show_refresh: bool = True,
) -> InlineKeyboardMarkup:
    """Кнопки обновления и возврата к карточке ключа."""
    builder = InlineKeyboardBuilder()
    if show_refresh:
        builder.row(
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=KeywordV3DecisionTraceRefresh(
                    keyword_setting_original_id=keyword_setting_original_id,
                    page=page,
                ).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к ключу",
            callback_data=KeywordV3DecisionTraceBack(
                keyword_setting_original_id=keyword_setting_original_id,
                page=page,
            ).pack(),
        )
    )
    return builder.as_markup()
