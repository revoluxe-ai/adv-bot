"""Экран последнего V3-решения по ключу (read-only audit из Redis)."""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.client_bot.user_interface.message_templates.templates import TextWithKeyboard
from app.client_bot.user_interface.views.keyword_v3_profile_ui import (
    NON_V3_DECISION_TRACE_MESSAGE,
    format_keyword_v3_decision_trace_screen,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.automatic_version_ui import (
    normalize_automatic_version_ui,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.shop_runner.service_manager.keyword_v3_decision_trace_ui.telegram.keyboard import (
    build_keyword_v3_decision_trace_keyboard,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.redis import (
    V3KeywordChangesRedisCache,
)
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.utils.db.session_maker import get_async_session_maker as sm


def _display_status_from_db_and_cache(
    keyword_setting: KeywordSetting,
    calculated_keyword: CalculatedKeyword | None,
) -> KeywordStatus:
    """Текущий статус для UI: из БД для 0/3/4, иначе из кеша."""
    hard = keyword_setting.hard_status
    if hard == 4:
        return KeywordStatus.GOOD
    if hard == 3:
        return KeywordStatus.BAD
    if hard == 0:
        return KeywordStatus.BAD
    if calculated_keyword is not None:
        return calculated_keyword.status
    return KeywordStatus.BAD


class KeywordV3DecisionTraceScreen(TextWithKeyboard):
    """Сообщение с последним записанным V3-решением по ключу."""

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
        """Загрузить audit из Redis и отправить экран."""
        async with sm(read_only=True) as session:
            stmt = (
                select(KeywordSetting)
                .options(selectinload(KeywordSetting.adv_setting))
                .where(KeywordSetting.id == self._keyword_setting_original_id)
            )
            result = await session.execute(stmt)
            keyword_setting = result.scalar_one_or_none()
        if keyword_setting is None:
            self._text = "Ключ не найден."
            self._keyboard = build_keyword_v3_decision_trace_keyboard(
                self._keyword_setting_original_id,
                self._page,
                show_refresh=False,
            )
            return await super().__call__(*args, **kwargs)

        adv_setting: AdvSetting = keyword_setting.adv_setting
        if normalize_automatic_version_ui(adv_setting.automatic_version) != 3:
            self._text = NON_V3_DECISION_TRACE_MESSAGE
            self._keyboard = build_keyword_v3_decision_trace_keyboard(
                self._keyword_setting_original_id,
                self._page,
                show_refresh=False,
            )
            return await super().__call__(*args, **kwargs)

        cache = RedisCalculatedKeywordsCacheManager()
        calculated_keyword = await cache.get_calculated_keyword(
            adv_setting.adv_id,
            keyword_setting.text,
        )
        display_status = _display_status_from_db_and_cache(
            keyword_setting,
            calculated_keyword,
        )
        nmids = [str(n) for n in list(adv_setting.nmids)]
        nmid_str = ", ".join(nmids) if nmids else "—"
        snapshot = await V3KeywordChangesRedisCache(adv_setting).get()
        self._text = format_keyword_v3_decision_trace_screen(
            nmid=nmid_str,
            keyword_text=keyword_setting.text,
            display_status=display_status,
            keyword_setting_id=self._keyword_setting_original_id,
            keyword_changes=snapshot,
        )
        self._keyboard = build_keyword_v3_decision_trace_keyboard(
            self._keyword_setting_original_id,
            self._page,
        )
        return await super().__call__(*args, **kwargs)
