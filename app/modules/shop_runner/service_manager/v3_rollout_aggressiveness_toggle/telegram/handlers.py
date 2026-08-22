"""Telegram: выбор ``AdvSetting.aggressiveness`` для Авто V3."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.views.callbacks import (
    V3RolloutAggMenuBack,
    V3RolloutAggMenuOpen,
    V3RolloutAggSet,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import (
    AdvSettingMenu,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard import (
    get_adv_setting_keyboard,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.v3_rollout_aggressiveness_ui import (
    FSM_V3_ROLLOUT_MENU_ADV_SETTING_ID,
    FSM_V3_ROLLOUT_PARENT_MESSAGE_ID,
    build_v3_rollout_submenu_markup,
    v3_rollout_submenu_caption,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.wb_adv_updater import data_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()
logger = logging.getLogger(__name__)

_ALLOWED_LEVELS: frozenset[int] = frozenset({1, 2, 3})


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


async def _clear_v3_rollout_fsm(state: FSMContext) -> None:
    await state.update_data(
        {
            FSM_V3_ROLLOUT_PARENT_MESSAGE_ID: None,
            FSM_V3_ROLLOUT_MENU_ADV_SETTING_ID: None,
        }
    )


@router.callback_query(V3RolloutAggMenuOpen.filter())
async def open_v3_rollout_menu(
    callback_query: CallbackQuery,
    callback_data: V3RolloutAggMenuOpen,
    bot: Bot,
    state: FSMContext,
) -> None:
    adv_setting_original_id = callback_data.adv_setting_original_id
    async with sm() as session:
        adv_result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv = adv_result.scalar_one_or_none()
        if adv is None or not adv.bot_active:
            if callback_query.message is not None:
                await bot.send_message(
                    callback_query.message.chat.id,
                    "Доступно только при версии АвтоАпдейтера V3.",
                )
            return
        markup = build_v3_rollout_submenu_markup(adv)

    assert callback_query.message
    msg = callback_query.message
    chat_id = msg.chat.id
    await state.update_data(
        {
            FSM_V3_ROLLOUT_PARENT_MESSAGE_ID: msg.message_id,
            FSM_V3_ROLLOUT_MENU_ADV_SETTING_ID: adv_setting_original_id,
        }
    )
    await bot.send_message(chat_id, v3_rollout_submenu_caption(), reply_markup=markup)


@router.callback_query(V3RolloutAggMenuBack.filter())
async def close_v3_rollout_menu(
    callback_query: CallbackQuery,
    bot: Bot,
    state: FSMContext,
) -> None:
    if callback_query.message is None:
        await _clear_v3_rollout_fsm(state)
        return

    chat_id = callback_query.message.chat.id
    fsm_data = await state.get_data()
    adv_setting_original_id = fsm_data.get(FSM_V3_ROLLOUT_MENU_ADV_SETTING_ID)

    await _clear_v3_rollout_fsm(state)

    if adv_setting_original_id is None:
        return

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


@router.callback_query(V3RolloutAggSet.filter())
async def set_v3_rollout_level(
    callback_query: CallbackQuery,
    callback_data: V3RolloutAggSet,
    bot: Bot,
    state: FSMContext,
) -> None:
    level = callback_data.level
    adv_setting_original_id = callback_data.adv_setting_original_id
    if level not in _ALLOWED_LEVELS:
        if callback_query.message is not None:
            await bot.send_message(
                callback_query.message.chat.id, "Недопустимое значение."
            )
        return

    async with sm() as session:
        adv_result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv_before = adv_result.scalar_one_or_none()
        if adv_before is None:
            if callback_query.message is not None:
                await bot.send_message(
                    callback_query.message.chat.id, "Кампания не найдена."
                )
            return
        if not adv_before.bot_active:
            if callback_query.message is not None:
                await bot.send_message(
                    callback_query.message.chat.id, "Только для V3."
                )
            return
        if int(adv_before.aggressiveness) == level:
            return
        await session.execute(
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"aggressiveness": level})
        )
        await session.commit()

    fsm_data = await state.get_data()
    parent_msg_id = fsm_data.get(FSM_V3_ROLLOUT_PARENT_MESSAGE_ID)
    stored_adv_id = fsm_data.get(FSM_V3_ROLLOUT_MENU_ADV_SETTING_ID)

    submenu_markup: InlineKeyboardMarkup | None = None
    parent_markup: InlineKeyboardMarkup | None = None
    async with sm() as session:
        adv_reload = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv_after = adv_reload.scalar_one()
        wb_uc = await _wb_user_cabinet_for_adv(
            session, adv_after, callback_query.from_user.id
        )
        submenu_markup = build_v3_rollout_submenu_markup(adv_after)
        if (
            parent_msg_id is not None
            and stored_adv_id == adv_setting_original_id
            and wb_uc is not None
        ):
            in_favorites = await data_manager.is_adv_in_favorites(
                adv_after.id, wb_uc.user_id
            )
            parent_markup = get_adv_setting_keyboard(wb_uc, adv_after, in_favorites)

    submenu_msg = callback_query.message
    if submenu_msg is None:
        return
    chat_id = submenu_msg.chat.id

    assert submenu_markup is not None
    try:
        if isinstance(submenu_msg, Message):
            await submenu_msg.edit_reply_markup(reply_markup=submenu_markup)
    except TelegramBadRequest as exc:
        logger.warning("v3 rollout submenu edit_reply_markup failed: %s", exc)

    parent_failed = False
    if parent_markup is not None and isinstance(parent_msg_id, int):
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=parent_msg_id,
                reply_markup=parent_markup,
            )
        except TelegramBadRequest as exc:
            parent_failed = True
            logger.warning(
                "v3 rollout parent edit_message_reply_markup failed chat=%s msg=%s: %s",
                chat_id,
                parent_msg_id,
                exc,
            )

    if parent_failed:
        await bot.send_message(
            chat_id,
            f"Уровень {level} сохранён. Если кнопка в главном меню не обновилась — "
            "нажмите «Назад» и откройте настройки РК снова.",
        )
