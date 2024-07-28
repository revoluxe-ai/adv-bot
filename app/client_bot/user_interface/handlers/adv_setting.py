import logging
import typing
from datetime import datetime
from typing import Union

import aiogram
from aiogram import Router, types, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.modules.wb_adv_updater.models import AdvPayment
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from .start import start_registration
from .. import states
from ..views import messages
from ..views import callbacks
from ... import const

sm = get_async_session_maker

router = Router()



logger = logging.getLogger(__name__)




@router.callback_query(callbacks.ChoiceAdvPaginator.filter(F.reset_filter == True))
async def reset_filter(callback: types.CallbackQuery, callback_data: callbacks.ChoiceAdvPaginator,
                          bot: aiogram.Bot, state: FSMContext):
     await callback.answer()
     wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
     await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
     await state.update_data(filter_advs=[])
     page = 1
     await messages.AdvCompanyChoicing(bot, state, callback.message.chat.id, wb_user_cabinet_original_id, page=page)()
     return


@router.message(StateFilter(states.AdvCompanyCatalog.waiting_for_keywords_for_filter))
async def waiting_for_keywords_for_filter(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    text = message.text
    if '/start' in text:
        await state.clear()
        await start_registration(message, bot, state)
        return
    filter_advs = text.splitlines()
    filter_advs = [keyword.strip().lower() for keyword in filter_advs if keyword]
    await state.update_data(filter_advs=filter_advs)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data['wb_user_cabinet_original_id']
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    page = 1
    check_data = await state.get_data()
    logger.debug(f'check_data: {check_data}')
    await messages.AdvCompanyChoicing \
        (bot, state, chat_id, wb_user_cabinet_original_id, page=page)()
    return




@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(callback: Union[types.CallbackQuery, types.Message],
                               callback_data: callbacks.ChoiceAdvPaginator,
                               bot: aiogram.Bot,
                               state: FSMContext):

    chat_id = callback.message.chat.id
    await bot.answer_callback_query(callback_query_id= callback.id)
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(state=states.AdvCompanyCatalog.waiting_for_keywords_for_filter)
    page = callback_data.page
    check_data = await state.get_data()
    logger.debug(f'check_data: {check_data}')
    await messages.AdvCompanyChoicing \
        (bot, state, chat_id, wb_user_cabinet_original_id, page=page)()
    return





@router.callback_query(callbacks.Adv.filter())
async def adv(callback: types.CallbackQuery, callback_data: callbacks.Adv,
              bot: aiogram.Bot, state: FSMContext):
    await callback.answer()
    await state.set_state(state = None)
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    await bot.answer_callback_query(callback.id)
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    data = await state.get_data()
    try:
        wb_user_cabinet_original_id = data['last_wb_user_cabinet_original_id']
    except KeyError:
        async with sm() as session:
            stmt = select(WBUserCabinet) \
                .join(WBUserCabinet.user) \
                .options(selectinload(WBUserCabinet.wb_cabinet) \
                         .selectinload(WBCabinet.adv_settings)) \
                .filter(User.user_telegram_id == callback.from_user.id,
                        AdvSetting.id == adv_original_id)
            wb_user_cabinet = await session.execute(stmt)
            wb_user_cabinet = wb_user_cabinet.scalar()
        wb_user_cabinet_original_id = wb_user_cabinet.id
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
    if not adv:
        await bot.send_message(callback.message.chat.id, 'Кампания не найдена, попробуйте еще раз')
        async with sm() as session:
            adv_settings = await session.execute(select(AdvSetting)\
                                                .join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id))\
            .order_by(AdvSetting.name)
            adv_settings = adv_settings.scalars().all()
        await messages.AdvCompanyChoicing\
            (bot, callback.message.chat.id, wb_user_cabinet_original_id, adv_settings)(state)
        return
    else:
        async with sm() as session:
            wb_user_cabinet = await session.execute(select(WBUserCabinet) \
                                                    .where(WBUserCabinet.id == wb_user_cabinet_original_id))
            wb_user_cabinet = wb_user_cabinet.scalar()
    chat_id = callback.message.chat.id
    try:
        await messages.AdvSettingMenu(bot,
                                                               chat_id,
                                                               wb_user_cabinet,
                                                               adv,
                                                               )()
    except NotItemsInAdvSetting:
        await messages.NoMainPhotos(bot, chat_id)()

    return


@router.callback_query(callbacks.TurnBot.filter(F.action == 'on'))
async def turn_adv_on(callback: types.CallbackQuery, state: FSMContext,
                      callback_data: callbacks.TurnBot,
                      bot: aiogram.Bot):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    adv_original_id = callback_data.adv_original_id
    async with sm() as session:
        session.begin()
        stmt = select(WBUserCabinet).join(WBUserCabinet.wb_cabinet)\
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = wb_user_cabinet.scalar()
        stmt = select(AdvSetting).options(selectinload(AdvSetting.payments))\
            .where(AdvSetting.id == adv_original_id)
        adv = await session.execute(stmt)
        adv: AdvSetting = adv.scalar()
        wb_cabinet = wb_user_cabinet.wb_cabinet
        if wb_cabinet.expiration_time < datetime.now():
            today = datetime.now().date()
            payments = adv.payments
            if not (bonus := wb_cabinet.bonus):
                bonus = 0
            if not (balance := wb_cabinet.balance):
                balance = 0
            if not any(payment.date == today for payment in payments):
                if bonus > const.PRICE_FOR_ADV_FOR_DAY:
                    payment = AdvPayment(date=datetime.now().date())
                    adv.payments.append(payment)
                    wb_cabinet.bonus -= const.PRICE_FOR_ADV_FOR_DAY
                elif balance > 0:
                    payment = AdvPayment()
                    payment.date = datetime.now().date()
                    session.add(payment)
                    adv.payments.append(payment)
                    wb_cabinet.balance -= const.PRICE_FOR_ADV_FOR_DAY
                else:
                    await callback.answer('На балансе недостаточно средств')
                    await messages.ShopMenu(bot,
                                            callback.message.chat.id,
                                            state,
                                            wb_user_cabinet_original_id)()
                    return
        await callback.answer('Включаю бота')
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
        await messages.AdvSettingMenu(bot,chat_id, wb_user_cabinet, adv)()
    return




@router.callback_query(callbacks.TurnBot.filter(F.action == 'off_all'))
async def turn_adv_off_all(callback: types.CallbackQuery, state: FSMContext,
                           callback_data: callbacks.TurnBot, bot: aiogram.Bot, ):
    await callback.answer('Выключаю всех ботов')
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        advs = await session.execute(select(AdvSetting).join(AdvSetting.wb_cabinet)\
        .join(WBCabinet.wb_user_cabinets)\
        .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        advs = advs.scalars().all()
        for adv in advs:
            adv.bot_active = False
        await session.commit()
    chat_id = callback.message.chat.id
    await messages.ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == 'off'))
async def turn_adv_off(callback: types.CallbackQuery, callback_data: callbacks.TurnBot, bot: aiogram.Bot, ):
    await callback.answer('Выключаю бота')
    adv_original_id = callback_data.adv_original_id
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv: AdvSetting = adv.scalar()

        adv.bot_active = False
        await session.commit()
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        wb_user_cabinet = await session.execute(select(WBUserCabinet) \
                                                .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        wb_user_cabinet = wb_user_cabinet.scalar()
    chat_id = callback.message.chat.id
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet,adv)()
    return
#
#
# @router.callback_query(callbacks.Min_ctr.filter(F.action == 'change'))
# async def change_min_ctr(callback: types.CallbackQuery,  callback_data: callbacks.Min_ctr,
#                          bot: aiogram.Bot, state: FSMContext, last_message:LastMessage):
#     await callback.answer()
#     adv_original_id = callback_data.adv_original_id
#     wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
#     async with sm() as session:
#         adv = await session.execute(select(AdvSetting)\
#                                     .where(AdvSetting.id == adv_original_id))
#         adv: AdvSetting = adv.scalar()
#     await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
#     await state.update_data(adv_original_id=adv_original_id)
#     await state.set_state(states.ChangeMinCTR.min_ctr)
#     last_message, message_type = await messages.GetMinCtr(bot, last_message,
#                                                            callback.message.chat.id, adv)()
#     return last_message, message_type
