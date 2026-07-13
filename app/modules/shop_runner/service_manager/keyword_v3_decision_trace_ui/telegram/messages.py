"""Экран последнего V3-решения по ключу (loader → pure formatter)."""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup

from app.client_bot.user_interface.message_templates.templates import TextWithKeyboard
from app.client_bot.user_interface.services.keyword_decision_trace_loader import (
    load_keyword_decision_trace_view,
)
from app.client_bot.user_interface.views.keyword_decision_trace_ui import (
    format_keyword_decision_trace_screen,
)
from app.modules.shop_runner.service_manager.keyword_v3_decision_trace_ui.telegram.keyboard import (
    build_keyword_v3_decision_trace_keyboard,
)


class KeywordV3DecisionTraceScreen(TextWithKeyboard):
    """Сообщение с cascade V3-решений по ключу (admin debug)."""

    parse_mode = ParseMode.MARKDOWN

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        keyword_setting_original_id: int,
        page: int,
    ) -> None:
        super().__init__(bot, chat_id)
        self._keyword_setting_original_id = keyword_setting_original_id
        self._page = page
        self._text = ""
        self._keyboard: InlineKeyboardMarkup | None = None

    @property
    def text(self) -> str:
        return self._text

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        assert self._keyboard is not None
        return self._keyboard

    async def __call__(self, *args, **kwargs) -> None:
        """Загрузить ViewData и отправить экран."""
        view = await load_keyword_decision_trace_view(
            keyword_setting_id=self._keyword_setting_original_id,
        )
        if view.keyword_text == "" and view.source == "empty":
            self._text = "Ключ не найден."
            self._keyboard = build_keyword_v3_decision_trace_keyboard(
                self._keyword_setting_original_id,
                self._page,
                show_refresh=False,
            )
            return await super().__call__(*args, **kwargs)

        self._text = format_keyword_decision_trace_screen(view)
        self._keyboard = build_keyword_v3_decision_trace_keyboard(
            self._keyword_setting_original_id,
            self._page,
            show_refresh=view.source != "non_v3",
        )
        return await super().__call__(*args, **kwargs)
