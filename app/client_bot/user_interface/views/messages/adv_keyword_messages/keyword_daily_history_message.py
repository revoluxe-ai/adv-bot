"""Экран детальной дневной истории по одному ключевому запросу."""

from __future__ import annotations

from datetime import date

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import keyboards
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.wb_adv_updater.keyword_daily_history import KeywordDailyHistoryManager
from app.modules.wb_adv_updater.keyword_daily_history.dto import KeywordDailyStat
from app.utils.db.session_maker import get_async_session_maker as sm


def format_keyword_daily_stat_block(stat: KeywordDailyStat) -> str:
    """Формирует многострочный блок статистики за один день."""
    avg_pos = f"{stat.avg_pos:.1f}" if stat.avg_pos > 0 else "—"
    pay_for_order = f"{stat.pay_for_order:.2f} ₽" if stat.orders > 0 else "—"
    return (
        f"{stat.date:%d.%m.%Y}\n"
        f"Поз.: {avg_pos} | CPM: {stat.cpm:.0f} ₽\n"
        f"Показы: {stat.views} | Клики: {stat.clicks} ({stat.ctr * 100:.2f}%)\n"
        f"Корз.: {stat.add_to_cart} | Заказы: {stat.orders}\n"
        f"Расход: {stat.spend:.2f} ₽ | Себес.: {pay_for_order}\n"
        f"Конв.: пок→корз. {stat.conv_views_to_cart * 100:.2f}% | "
        f"корз→зак. {stat.conv_cart_to_order * 100:.2f}% | "
        f"пок→зак. {stat.conv_views_to_order * 100:.2f}%"
    )


def build_keyword_daily_history_text(
    keyword_text: str,
    nmids: list[int],
    page: int,
    total_pages: int,
    page_range: tuple[date, date] | None,
    stats: list[KeywordDailyStat],
) -> str:
    """Собирает текст экрана истории по дням."""
    keyword_text = keyword_text.replace("\n", " ").strip()
    nmids_text = ", ".join(map(str, nmids)) if nmids else "—"
    header = (
        f"История по дням (стр. {page}/{total_pages})\n"
        f"Ключ: {keyword_text}\n"
        f"Артикулы: {nmids_text}\n"
    )
    if page_range is not None:
        start_date, end_date = page_range
        header += f"{start_date:%d.%m.%Y}–{end_date:%d.%m.%Y}\n"

    if not stats:
        return header + "\nНет данных за выбранный период"

    body = "\n\n".join(
        format_keyword_daily_stat_block(stat)
        for stat in sorted(stats, key=lambda item: item.date, reverse=True)
    )
    return header + "\n" + body


class KeywordDailyHistoryScreen(TextWithKeyboard):
    """Экран со страницами дневной истории по одному ключу."""

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        keyword_setting_original_id: int,
        page: int,
        page_size: int = 7,
    ) -> None:
        super().__init__(bot, chat_id)
        self._keyword_setting_original_id = keyword_setting_original_id
        self._page = page
        self._page_size = page_size
        self._manager = KeywordDailyHistoryManager()
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
        """Загружает данные и отправляет сообщение с историей."""
        async with sm() as session:
            stmt = (
                select(KeywordSetting)
                .options(selectinload(KeywordSetting.adv_setting))
                .where(KeywordSetting.id == self._keyword_setting_original_id)
            )
            result = await session.execute(stmt)
            keyword_setting: KeywordSetting = result.scalar_one()
            adv_setting: AdvSetting = keyword_setting.adv_setting

        stats, current_page, total_pages, page_range = await self._manager.get_history_page(
            keyword_setting,
            adv_setting,
            self._page,
            self._page_size,
        )
        self._text = build_keyword_daily_history_text(
            keyword_setting.text,
            list(adv_setting.nmids),
            current_page,
            total_pages,
            page_range,
            stats,
        )
        self._keyboard = keyboards.get_keyword_daily_history_keyboard(
            keyword_setting.id,
            current_page,
            total_pages,
        )
        return await super().__call__(*args, **kwargs)
