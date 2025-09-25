import logging

import aiogram
from aiogram import Bot, F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.modules import balance_manager
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from .. import states
from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()


logger = logging.getLogger(__name__)

pricer = Pricer()


@router.callback_query(callbacks.ChoiceAdvPaginator.filter(F.reset_filter))
async def reset_filter(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.update_data(filter_advs=[])

    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result.scalars().all())

    page = 1
    message = callback.message
    if not isinstance(message, types.Message):
        return
    await messages.AdvCompanyChoicing(
        bot,
        message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
        page=page,
    )()

    return


@router.message(StateFilter(states.AdvCompanyCatalog.waiting_for_keywords_for_filter))
async def waiting_for_keywords_for_filter(message: types.Message, bot: Bot, state: FSMContext) -> None:
    chat_id = message.chat.id
    text = message.text
    if text is None:
        return
    filter_advs = text.splitlines()
    filter_advs = [keyword.strip().lower() for keyword in filter_advs if keyword]
    await state.update_data(filter_advs=filter_advs)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int = state_data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result2 = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result2.scalars().all())

    page = 1
    check_data = await state.get_data()
    logger.debug(f"check_data: {check_data}")
    await messages.AdvCompanyChoicing(bot, chat_id, wb_user_cabinet_original_id, adv_settings, state, page=page)()
    return


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if not isinstance(callback.message, types.Message):
        return
    chat_id = callback.message.chat.id
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(state=states.AdvCompanyCatalog.waiting_for_keywords_for_filter)
    page = callback_data.page
    check_data = await state.get_data()
    logger.debug(f"check_data: {check_data}")
    stmt = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    async with sm() as session:
        result3 = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result3.scalars().all())
    await messages.AdvCompanyChoicing(bot, chat_id, wb_user_cabinet_original_id, adv_settings, state, page=page)()
    return


@router.callback_query(callbacks.Adv.filter())
async def adv_handler(
    callback: types.CallbackQuery,
    callback_data: callbacks.Adv,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    await state.set_state()
    if not isinstance(callback.message, types.Message):
        return
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    data = await state.get_data()

    try:
        wb_user_cabinet_original_id = data["last_wb_user_cabinet_original_id"]
    except KeyError:
        async with sm() as session:
            stmt = (
                select(WBUserCabinet)
                .join(WBUserCabinet.user)
                .join(WBUserCabinet.wb_cabinet)
                .join(WBCabinet.adv_settings)
                .filter(
                    User.user_telegram_id == callback.from_user.id,  # Фильтрация по user_telegram_id
                    AdvSetting.id == adv_original_id,  # Фильтрация по нужному AdvSetting
                )
            )
            result = await session.execute(stmt)
            wb_user_cabinet = result.scalar_one_or_none()
        if wb_user_cabinet is None:
            return
        wb_user_cabinet_original_id = wb_user_cabinet.id

    async with sm() as session:
        result_adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = result_adv.scalar_one_or_none()

    if not adv:
        await bot.send_message(callback.message.chat.id, "Кампания не найдена, попробуйте еще раз")
        advs_stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .order_by(AdvSetting.name)
        )
        async with sm() as session:
            adv_settings_result = await session.execute(advs_stmt)
            adv_settings: list[AdvSetting] = list(adv_settings_result.scalars().all())

        await messages.AdvCompanyChoicing(
            bot,
            callback.message.chat.id,
            wb_user_cabinet_original_id,
            adv_settings,
            state,
        )()
        return

    async with sm() as session:
        result_uc = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet = result_uc.scalar_one_or_none()

    chat_id = callback.message.chat.id
    try:
        if wb_user_cabinet is None or adv is None:
            return
        await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()
    except NotItemsInAdvSetting:
        await messages.NoMainPhotos(bot, chat_id)(adv)

    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "on"))
async def turn_adv_on(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
) -> None:
    if not isinstance(callback.message, types.Message):
        return
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=False) as session:
        session.begin()
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.wb_cabinet)
            .options(selectinload(WBUserCabinet.wb_cabinet))
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result_uc = await session.execute(stmt)
        wb_user_cabinet = result_uc.scalar_one_or_none()
        if wb_user_cabinet is None:
            await bot.send_message(callback.message.chat.id, "Кабинет не найден")
            return
        stmt_adv = select(AdvSetting).options(selectinload(AdvSetting.payments)).where(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt_adv)
        adv = result.scalar_one_or_none()
        if adv is None:
            await bot.send_message(callback.message.chat.id, "Кампания не найдена")
            return
        wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
        tariff_for_month = await pricer.get_price_for_day_for_shop(wb_cabinet.shop_id)
        price_for_adv_for_day = pricer.get_tariff_for_day(tariff_for_month)
        balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(wb_cabinet.id)
        sum_balance = balance + bonus
        if not sum_balance >= price_for_adv_for_day:
            await bot.send_message(callback.message.chat.id, "Недостаточно средств")
            await ShopMenu(bot, callback.message.chat.id, state, wb_user_cabinet_original_id)()
            return
        await bot.send_message(callback.message.chat.id, "Включаю бота")
        adv.bot_active = True
        await session.commit()
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
        await state.update_data(adv_original_id=adv.id)
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        stmt_uc2 = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        result2 = await session.execute(stmt_uc2)
        wb_user_cabinet = result2.scalar_one_or_none()
        chat_id = callback.message.chat.id
        if wb_user_cabinet is None:
            return
        await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "off_all"))
async def turn_adv_off_all(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
) -> None:
    if not isinstance(callback.message, types.Message):
        return
    await bot.send_message(callback.message.chat.id, "Отключаю бота от всех кампаний")
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=False) as session:
        advs = await session.execute(
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        advs_list: list[AdvSetting] = list(advs.scalars().all())
        for adv_ in advs_list:
            adv_.bot_active = False
        await session.commit()
    chat_id = callback.message.chat.id
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "off"))
async def turn_adv_off(call: types.CallbackQuery, callback_data: callbacks.TurnBot, bot: aiogram.Bot) -> None:
    if not isinstance(call.message, types.Message):
        return
    # data = await state.get_data()
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = (
            select(WBUserCabinet).join(WBUserCabinet.wb_cabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result_uc = await session.execute(stmt)
        wb_user_cabinet = result_uc.scalar_one_or_none()

    async with sm(read_only=False) as session:
        result = await session.execute(select(AdvSetting).where(AdvSetting.id == callback_data.adv_original_id))
        adv_setting = result.scalar_one_or_none()
        if adv_setting is None:
            return
        adv_setting.bot_active = False
        await session.commit()

    await messages.AdvSettingMenu(
        bot,
        call.message.chat.id,
        wb_user_cabinet if wb_user_cabinet is not None else WBUserCabinet(),
        adv_setting,
    )()


@router.callback_query(callbacks.ChangeAutoMinCTR.filter(F.action == "turn_on_auto_min_ctr"))
async def turn_on_auto_min_ctr(callback: types.CallbackQuery, bot: Bot, callback_data: callbacks.ChangeAutoMinCTR) -> None:
    if not isinstance(callback.message, types.Message):
        return
    adv_setting_original_id = callback_data.adv_setting_original_id
    stmt = (
        update(AdvSetting)
        .where(AdvSetting.id == callback_data.adv_setting_original_id)
        .values({AdvSetting.new_auto_min_ctr_mode: True})
    )

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await messages.SettingMinCTR(bot, callback.message.chat.id)(adv_setting_original_id)


@router.callback_query(callbacks.ChangeAutoMinCTR.filter(F.action == "turn_off_auto_min_ctr"))
async def turn_off_auto_min_ctr(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeAutoMinCTR,
    bot: Bot,
) -> None:
    if not isinstance(callback.message, types.Message):
        return
    adv_setting_original_id = callback_data.adv_setting_original_id

    stmt = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_original_id)
        .values({AdvSetting.new_auto_min_ctr_mode: False})
    )

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await messages.SettingMinCTR(bot, callback.message.chat.id)(adv_setting_original_id)
