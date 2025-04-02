import logging
import typing
from datetime import datetime
from typing import Union

import aiogram
from aiogram import Router, types, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.utils.pricer.pricer import Pricer
from .. import states
from ..views import messages
from ..views import callbacks
from ... import const

sm = get_async_session_maker

router = Router()


logger = logging.getLogger(__name__)

pricer = Pricer()


@router.callback_query(callbacks.ChoiceAdvPaginator.filter(F.reset_filter))
async def reset_filter(callback: types.CallbackQuery,
                       callback_data: callbacks.ChoiceAdvPaginator,
                       bot: aiogram.Bot, state: FSMContext) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.update_data(filter_advs=[])

    async with sm() as session:
        stmt = select(AdvSetting).join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        adv_settings = await session.execute(stmt)
        adv_settings = adv_settings.scalars().all()

    page = 1
    await messages.AdvCompanyChoicing(
        bot,
        callback.message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
        page=page)()

    return


@router.message(StateFilter(states.AdvCompanyCatalog.waiting_for_keywords_for_filter))
async def waiting_for_keywords_for_filter(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    text = message.text
    filter_advs = text.splitlines()
    filter_advs = [keyword.strip().lower() for keyword in filter_advs if keyword]
    await state.update_data(filter_advs=filter_advs)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int = state_data['last_wb_user_cabinet_original_id']
    async with sm() as session:
        stmt = select(AdvSetting).join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        adv_settings = await session.execute(stmt)
        adv_settings = adv_settings.scalars().all()

    page = 1
    check_data = await state.get_data()
    logger.debug(f'check_data: {check_data}')
    await messages.AdvCompanyChoicing(
        bot,
        chat_id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
        page=page)()
    return


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(callback: Union[types.CallbackQuery, types.Message],
                               callback_data: callbacks.ChoiceAdvPaginator,
                               bot: aiogram.Bot,
                               state: FSMContext):

    chat_id = callback.message.chat.id
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(state=states.AdvCompanyCatalog.waiting_for_keywords_for_filter)
    page = callback_data.page
    check_data = await state.get_data()
    logger.debug(f'check_data: {check_data}')
    stmt = select(AdvSetting)\
        .join(AdvSetting.wb_cabinet)\
        .join(WBCabinet.wb_user_cabinets)\
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    async with sm() as session:
        adv_settings = await session.execute(stmt)
        adv_settings = adv_settings.scalars().all()

    await messages.AdvCompanyChoicing(
        bot,
        chat_id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
        page=page)()
    return


@router.callback_query(callbacks.Adv.filter())
async def adv(
        callback: types.CallbackQuery,
        callback_data: callbacks.Adv,
        bot: aiogram.Bot,
        state: FSMContext,
):
    await state.set_state()
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
            wb_user_cabinet = result.scalar()  # Извлекаем первую строку
        wb_user_cabinet_original_id: int = wb_user_cabinet.id

    async with sm() as session:
        adv_ = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv_ = adv_.scalar()

    if not adv_:
        await bot.send_message(callback.message.chat.id, "Кампания не найдена, попробуйте еще раз")
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .order_by(AdvSetting.name)
        )
        async with sm() as session:
            adv_settings = await session.execute(stmt)
            adv_settings = adv_settings.scalars().all()

        await messages.AdvCompanyChoicing(
            bot, callback.message.chat.id, wb_user_cabinet_original_id, adv_settings, state
        )()
        return

    async with sm() as session:
        wb_user_cabinet = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet = wb_user_cabinet.scalar()

    chat_id = callback.message.chat.id
    try:
        await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()
    except NotItemsInAdvSetting:
        await messages.NoMainPhotos(bot, chat_id)(adv)

    return


@router.callback_query(callbacks.TurnBot.filter(F.action == 'on'))
async def turn_adv_on(callback: types.CallbackQuery, state: FSMContext,
                      callback_data: callbacks.TurnBot,
                      bot: aiogram.Bot) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    adv_original_id = callback_data.adv_original_id
    async with (sm(read_only=False) as session):
        session.begin()
        stmt = select(WBUserCabinet).join(WBUserCabinet.wb_cabinet)\
                                    .options(selectinload(WBUserCabinet.wb_cabinet))\
                                    .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = wb_user_cabinet.scalar()
        stmt = select(AdvSetting).options(selectinload(AdvSetting.payments))\
            .where(AdvSetting.id == adv_original_id)
        adv_ = await session.execute(stmt)
        adv_: AdvSetting = adv_.scalar()
        wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
        tariff_for_month = await pricer.get_price_for_day_for_shop(wb_cabinet.shop_id)
        price_for_adv_for_day = pricer.get_tariff_for_day(tariff_for_month)
        if wb_cabinet.expiration_time < datetime.now():
            if not (bonus := wb_cabinet.bonus):
                bonus = 0
            if not (balance := wb_cabinet.balance):
                balance = 0
            sum_balance = balance + bonus
            if not sum_balance >= price_for_adv_for_day:
                await bot.send_message(callback.message.chat.id, 'Недостаточно средств')
                await ShopMenu(
                    bot,
                    callback.message.chat.id,
                    state,
                    wb_user_cabinet_original_id)()
                return
        await bot.send_message(callback.message.chat.id, 'Включаю бота')
        adv.bot_active = True
        await session.commit()
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
        await state.update_data(adv_original_id=adv.id)
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        stmt = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar()
        chat_id = callback.message.chat.id
        await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == 'off_all'))
async def turn_adv_off_all(callback: types.CallbackQuery, state: FSMContext,
                           callback_data: callbacks.TurnBot, bot: aiogram.Bot, ):
    await bot.send_message(callback.message.chat.id, 'Отключаю бота от всех кампаний')
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=False) as session:
        advs = await session.execute(select(AdvSetting).join(AdvSetting.wb_cabinet)
                                                       .join(WBCabinet.wb_user_cabinets)
                                                       .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        advs = advs.scalars().all()
        for adv_ in advs:
            adv_.bot_active = False
        await session.commit()
    chat_id = callback.message.chat.id
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == 'off'))
async def turn_adv_off(call: types.CallbackQuery,
                       callback_data: callbacks.TurnBot,
                       bot: aiogram.Bot):
    # data = await state.get_data()
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = select(WBUserCabinet).join(WBUserCabinet.wb_cabinet) \
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar()

    async with sm(read_only=False) as session:
        adv_setting = await session.execute(select(AdvSetting).where(AdvSetting.id == callback_data.adv_original_id))
        adv_setting: AdvSetting = adv_setting.scalars().first()
        adv_setting.bot_active = False
        await session.commit()

    await messages.AdvSettingMenu(bot,
                                  call.message.chat.id,
                                  wb_user_cabinet,
                                  adv_setting, )()


@router.callback_query(callbacks.ChangeAutoMinCTR.filter(F.action == 'turn_on_auto_min_ctr'))
async def turn_on_auto_min_ctr(callback: types.CallbackQuery,
                               bot: Bot,
                               callback_data: callbacks.ChangeAutoMinCTR):
    adv_setting_original_id = callback_data.adv_setting_original_id
    stmt = update(AdvSetting) \
        .where(AdvSetting.id == callback_data.adv_setting_original_id) \
        .values({AdvSetting.new_auto_min_ctr_mode: True})

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await messages.SettingMinCTR(bot,
                                 callback.message.chat.id)(adv_setting_original_id)


@router.callback_query(callbacks.ChangeAutoMinCTR.filter(F.action == 'turn_off_auto_min_ctr'))
async def turn_off_auto_min_ctr(callback: types.CallbackQuery,
                                callback_data: callbacks.ChangeAutoMinCTR,
                                bot: Bot,):
    adv_setting_original_id = callback_data.adv_setting_original_id

    stmt = update(AdvSetting) \
        .where(AdvSetting.id == adv_setting_original_id)\
        .values({AdvSetting.new_auto_min_ctr_mode: False})

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await messages.SettingMinCTR(bot, callback.message.chat.id)(adv_setting_original_id)
