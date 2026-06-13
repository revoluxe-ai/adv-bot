"""Telegram: toggle ``AdvSetting.v3_substitute_fact_cpo_for_max`` (V3 Raise MAX)."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.views.callbacks import V3SubstituteFactCpoToggle
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import (
    AdvSettingMenu,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard import (
    get_adv_setting_keyboard,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.automatic_version_ui import (
    normalize_automatic_version_ui,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.wb_adv_updater import data_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()
logger = logging.getLogger(__name__)


async def _wb_user_cabinet_for_adv(
    session: AsyncSession,
    adv_setting: AdvSetting,
    telegram_user_id: int,
) -> WBUserCabinet | None:
    stmt = (
        select(WBUserCabinet)
        .options(joinedload(WBUserCabinet.wb_cabinet))
        .join(User, User.id == WBUserCabinet.user_id)
        .where(User.user_telegram_id == telegram_user_id)
        .where(WBUserCabinet.wb_cabinet_id == adv_setting.wb_cabinet_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.callback_query(V3SubstituteFactCpoToggle.filter())
async def toggle_v3_substitute_fact_cpo_for_max(
    callback_query: CallbackQuery,
    callback_data: V3SubstituteFactCpoToggle,
) -> None:
    """Переключить Raise MAX и обновить клавиатуру меню РК."""
    adv_setting_original_id = callback_data.adv_setting_original_id
    new_status = bool(callback_data.new_status)

    async with sm() as session:
        adv_result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv_before = adv_result.scalar_one_or_none()
        if adv_before is None:
            if callback_query.message is not None:
                await callback_query.message.answer("Кампания не найдена.")
            return
        if normalize_automatic_version_ui(adv_before.automatic_version) != 3:
            if callback_query.message is not None:
                await callback_query.message.answer("Доступно только при версии Авто V3.")
            return
        if bool(adv_before.v3_substitute_fact_cpo_for_max) == new_status:
            return
        await session.execute(
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"v3_substitute_fact_cpo_for_max": new_status})
        )
        await session.commit()

    if callback_query.message is None:
        return

    chat_id = callback_query.message.chat.id
    telegram_user_id = callback_query.from_user.id

    async with sm() as session:
        adv_reload = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv_after = adv_reload.scalar_one()
        wb_uc = await _wb_user_cabinet_for_adv(session, adv_after, telegram_user_id)
        if wb_uc is None:
            await callback_query.message.answer(
                "Не удалось определить кабинет. Откройте РК из списка кампаний."
            )
            return
        in_favorites = await data_manager.is_adv_in_favorites(
            adv_after.id, wb_uc.user_id
        )
        markup = get_adv_setting_keyboard(wb_uc, adv_after, in_favorites)

    try:
        await callback_query.message.edit_reply_markup(reply_markup=markup)
    except TelegramBadRequest as exc:
        logger.warning("v3 raise max toggle edit_reply_markup failed: %s", exc)
        await AdvSettingMenu(callback_query.bot, chat_id, wb_uc, adv_after)()
