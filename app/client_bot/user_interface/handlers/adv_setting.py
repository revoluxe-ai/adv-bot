import logging
from datetime import datetime

import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.modules.wb_adv_updater.models import AdvPayment
from app.utils.db.session_maker import get_async_session_maker

from ..views import callbacks, messages
from ..views.callbacks import Action
from ... import const

sm = get_async_session_maker

router = Router()



logger = logging.getLogger(__name__)





@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(callback: types.CallbackQuery,
                               callback_data: callbacks.ChoiceAdvPaginator,
                               bot: aiogram.Bot,
                               state: FSMContext):

    await bot.answer_callback_query(callback_query_id=callback.id)
    await callback.message.answer("Пожалуйста подождите, эта операция займет немного времени")

    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    page = callback_data.page
    check_data = await state.get_data()
    logger.debug(f'check_data: {check_data}')

    chat_id = callback.message.chat.id

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
    wb_user_cabinet_original_id = data['last_wb_user_cabinet_original_id']
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
        await messages.NotItemsInAdvSetting(bot, chat_id, wb_user_cabinet, adv)()

    return


@router.callback_query(callbacks.TurnAdv.filter(F.action == 'on'))
async def turn_adv_on(callback: types.CallbackQuery, state: FSMContext,
                      callback_data: callbacks.TurnAdv,
                      bot: aiogram.Bot):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    adv_original_id = callback_data.adv_original_id
    async with sm() as session:
        session.begin()
        stmt = select(WBCabinet).join(WBUserCabinet.wb_cabinet)\
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        wb_cabinet = await session.execute(stmt)
        wb_cabinet: WBCabinet = wb_cabinet.scalar()
        stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        adv = await session.execute(stmt)
        adv: AdvSetting = adv.scalar()
        if wb_cabinet.expiration_time < datetime.now():
            today = datetime.now().date()
            if adv.payments.filter(AdvPayment.date == today).count() == 0:
                if wb_cabinet.balance > const.PRICE_FOR_ADV_FOR_DAY:
                    payment = AdvPayment()
                    payment.date = datetime.now().date()
                    adv.payments.append(payment)
                    wb_cabinet.balance -= const.PRICE_FOR_ADV_FOR_DAY
                else:
                    await callback.answer('На балансе недостаточно средств')
                    return
    await callback.answer('Включаю бота')
    adv_id = callback_data.adv_original_id
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
        adv: AdvSetting = adv.scalar()
        adv.bot_active = True
        await session.commit()
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.update_data(adv_original_id=adv_id)
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
         wb_user_cabinet = await session.execute(select(WBUserCabinet) \
                                                .where(WBUserCabinet.id == wb_user_cabinet_original_id))
         wb_user_cabinet = wb_user_cabinet.scalar()
    chat_id = callback.message.chat.id
    await messages.AdvSettingMenu(bot,chat_id, wb_user_cabinet, adv)()
    return


@router.callback_query(callbacks.TurnAdv.filter(F.action == 'off'))
async def turn_adv_off(callback: types.CallbackQuery, callback_data: callbacks.TurnAdv, bot: aiogram.Bot,):
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
