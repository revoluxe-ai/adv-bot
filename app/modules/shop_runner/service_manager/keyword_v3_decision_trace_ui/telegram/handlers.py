"""Telegram handlers: экран последнего V3-решения по ключу (admin debug)."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.user_interface.views import messages
from app.client_bot.user_interface.views.callbacks import (
    KeywordV3DecisionTraceBack,
    KeywordV3DecisionTraceOpen,
    KeywordV3DecisionTraceRefresh,
)
from app.client_bot.user_interface.views.keyword_v3_profile_ui import (
    NON_V3_DECISION_TRACE_MESSAGE,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.shop_runner.service_manager.keyword_v3_decision_trace_ui.telegram.messages import (
    KeywordV3DecisionTraceScreen,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()
logger = logging.getLogger(__name__)

_ACCESS_DENIED = "Нет доступа"


async def _notify_callback_user(bot: Bot, callback: CallbackQuery, text: str) -> None:
    """Отправить текст пользователю без повторного ``CallbackQuery.answer``."""
    if callback.message is None:
        return
    _ = await bot.send_message(callback.message.chat.id, text)


async def _require_admin(bot: Bot, callback: CallbackQuery) -> bool:
    """Проверка admin/debug доступа для callback."""
    if not callback.from_user:
        return False
    if not is_bot_admin(callback.from_user.id):
        await _notify_callback_user(bot, callback, _ACCESS_DENIED)
        return False
    return True


async def _is_v3_keyword(keyword_setting_original_id: int) -> bool:
    """Проверить, что ключ принадлежит кампании с V3-управлением."""
    async with sm(read_only=True) as session:
        stmt = (
            select(KeywordSetting)
            .options(selectinload(KeywordSetting.adv_setting))
            .where(KeywordSetting.id == keyword_setting_original_id)
        )
        result = await session.execute(stmt)
        keyword_setting = result.scalar_one_or_none()
    if keyword_setting is None:
        return False
    adv: AdvSetting = keyword_setting.adv_setting
    return adv.bot_active


@router.callback_query(KeywordV3DecisionTraceOpen.filter())
async def open_keyword_v3_decision_trace(
    callback: CallbackQuery,
    callback_data: KeywordV3DecisionTraceOpen,
    bot: Bot,
) -> None:
    """Открыть экран последнего V3-решения по ключу."""
    if callback.message is None:
        return
    if not await _require_admin(bot, callback):
        return
    if not await _is_v3_keyword(callback_data.keyword_setting_original_id):
        await _notify_callback_user(bot, callback, NON_V3_DECISION_TRACE_MESSAGE)
        return
    async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
        await KeywordV3DecisionTraceScreen(
            bot=bot,
            chat_id=callback.message.chat.id,
            keyword_setting_original_id=callback_data.keyword_setting_original_id,
            page=callback_data.page,
        )()


@router.callback_query(KeywordV3DecisionTraceRefresh.filter())
async def refresh_keyword_v3_decision_trace(
    callback: CallbackQuery,
    callback_data: KeywordV3DecisionTraceRefresh,
    bot: Bot,
) -> None:
    """Перечитать Redis и отправить обновлённый экран."""
    if callback.message is None:
        return
    if not await _require_admin(bot, callback):
        return
    if not await _is_v3_keyword(callback_data.keyword_setting_original_id):
        await _notify_callback_user(bot, callback, NON_V3_DECISION_TRACE_MESSAGE)
        return
    async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
        await KeywordV3DecisionTraceScreen(
            bot=bot,
            chat_id=callback.message.chat.id,
            keyword_setting_original_id=callback_data.keyword_setting_original_id,
            page=callback_data.page,
        )()


@router.callback_query(KeywordV3DecisionTraceBack.filter())
async def back_from_keyword_v3_decision_trace(
    callback: CallbackQuery,
    callback_data: KeywordV3DecisionTraceBack,
    bot: Bot,
) -> None:
    """Вернуться к карточке ключа."""
    if callback.message is None:
        return
    if not await _require_admin(bot, callback):
        return
    telegram_user_id = callback.from_user.id if callback.from_user else None
    await messages.KeywordSettingMessage(
        bot,
        callback.message.chat.id,
        callback_data.keyword_setting_original_id,
        callback_data.page,
        telegram_user_id=telegram_user_id,
    )()
