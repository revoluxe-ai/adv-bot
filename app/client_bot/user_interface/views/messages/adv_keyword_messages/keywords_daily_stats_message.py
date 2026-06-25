"""Экран дневной статистики для страницы ключей кампании."""

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import keyboards
from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import (
    CommonStatDataManager,
    DaysStatTextOptions,
)
from app.modules.common_slaves.wildberries.models import AdvSetting


class KeywordsDailyStatsScreen(TextWithKeyboard):
    """Текстовый экран с дневной статистикой по ключам за 14-дневные страницы."""

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        adv_setting: AdvSetting,
        page: int,
        keywords_page: int,
        sort_mode: str,
        page_size: int = 14,
    ) -> None:
        super().__init__(bot, chat_id)
        self._adv_setting = adv_setting
        self._page = page
        self._keywords_page = keywords_page
        self._sort_mode = sort_mode
        self._page_size = page_size
        self._manager = CommonStatDataManager()
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
        """Подготавливает текст и клавиатуру перед отправкой сообщения."""
        text, page, total_pages = await self._manager.get_days_static_text_page(
            self._adv_setting,
            self._page,
            options=DaysStatTextOptions(
                show_forecast=False,
                show_clicks_warning=False,
                show_organic_pct=True,
            ),
            page_size=self._page_size,
        )
        earliest_date = await self._manager.get_earliest_stat_date(self._adv_setting)
        page_range = self._manager.page_to_date_range(
            page, self._page_size, earliest_date=earliest_date
        )

        if text and page_range is not None:
            start_date, end_date = page_range
            body = text.removeprefix("\n\nСтатистика по дням:\n")
            self._text = (
                f"Статистика по дням (стр. {page}/{total_pages})\n"
                f"{start_date.strftime('%d.%m.%Y')}–{end_date.strftime('%d.%m.%Y')}\n"
                f"{body}"
            )
        else:
            self._text = "Нет данных за выбранный период"

        self._keyboard = keyboards.get_keywords_daily_stats_keyboard(
            self._adv_setting.id,
            page,
            total_pages,
            self._keywords_page,
            self._sort_mode,
        )
        return await super().__call__(*args, **kwargs)
