"""Telegram handlers: отчёт последнего V3-тика."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.views.callbacks import (
    V3TickReportBack,
    V3TickReportOpen,
    V3TickReportRefresh,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import (
    AdvSettingMenu,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.v3_tick_report_ui import (
    FSM_V3_TICK_REPORT_ADV_SETTING_ID,
    FSM_V3_TICK_REPORT_PARENT_MESSAGE_ID,
    build_v3_tick_report_keyboard,
)
from app.client_bot.user_interface.views.messages.v3_tick_report_informer import (
    format_v3_tick_report_text,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_redis import (
    V3TickReportRedisCache,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()
logger = logging.getLogger(__name__)


async def _wb_user_cabinet_for_adv(
    session,
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


async def _clear_tick_report_fsm(state: FSMContext) -> None:
    await state.update_data(
        {
            FSM_V3_TICK_REPORT_PARENT_MESSAGE_ID: None,
            FSM_V3_TICK_REPORT_ADV_SETTING_ID: None,
        }
    )


async def _load_report_text(adv: AdvSetting) -> str:
    snapshot = await V3TickReportRedisCache(adv).get()
    return format_v3_tick_report_text(snapshot)


@router.callback_query(V3TickReportOpen.filter())
async def open_v3_tick_report(
    callback_query: CallbackQuery,
    callback_data: V3TickReportOpen,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Открыть новое сообщение с отчётом последнего V3-тика."""
    adv_setting_original_id = callback_data.adv_setting_original_id
    async with sm() as session:
        adv_result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv = adv_result.scalar_one_or_none()
    if adv is None or callback_query.message is None:
        if callback_query.message is not None:
            await bot.send_message(
                callback_query.message.chat.id, "Кампания не найдена."
            )
        return
    text = await _load_report_text(adv)
    markup = build_v3_tick_report_keyboard(adv_setting_original_id)
    chat_id = callback_query.message.chat.id
    await state.update_data(
        {
            FSM_V3_TICK_REPORT_PARENT_MESSAGE_ID: callback_query.message.message_id,
            FSM_V3_TICK_REPORT_ADV_SETTING_ID: adv_setting_original_id,
        }
    )
    await bot.send_message(chat_id, text, reply_markup=markup)


@router.callback_query(V3TickReportRefresh.filter())
async def refresh_v3_tick_report(
    callback_query: CallbackQuery,
    callback_data: V3TickReportRefresh,
    bot: Bot,
) -> None:
    """Перечитать Redis и отправить новое сообщение с отчётом (без edit_text)."""
    if callback_query.message is None:
        return
    adv_setting_original_id = callback_data.adv_setting_original_id
    chat_id = callback_query.message.chat.id
    async with sm() as session:
        adv_result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv = adv_result.scalar_one_or_none()
    if adv is None:
        await bot.send_message(chat_id, "Кампания не найдена.")
        return
    text = await _load_report_text(adv)
    markup = build_v3_tick_report_keyboard(adv_setting_original_id)
    await bot.send_message(chat_id, text, reply_markup=markup)


@router.callback_query(V3TickReportBack.filter())
async def back_from_v3_tick_report(
    callback_query: CallbackQuery,
    callback_data: V3TickReportBack,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Вернуться к главному меню настроек РК."""
    if callback_query.message is None:
        await _clear_tick_report_fsm(state)
        return
    chat_id = callback_query.message.chat.id
    adv_setting_original_id = callback_data.adv_setting_original_id
    await _clear_tick_report_fsm(state)
    telegram_user_id = callback_query.from_user.id
    async with sm() as session:
        adv_result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == int(adv_setting_original_id))
        )
        adv = adv_result.scalar_one_or_none()
        if adv is None:
            return
        wb_uc = await _wb_user_cabinet_for_adv(session, adv, telegram_user_id)
    if wb_uc is None:
        await bot.send_message(
            chat_id,
            "Не удалось определить кабинет. Откройте РК из списка кампаний.",
        )
        return
    await AdvSettingMenu(bot, chat_id, wb_uc, adv)()
