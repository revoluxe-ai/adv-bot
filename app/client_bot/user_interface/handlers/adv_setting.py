import logging
import typing
from datetime import datetime
from typing import Union

import aiogram
from aiogram import Router, types, F, Bot
from aiogram.filters import StateFilter, BaseFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
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

class AdminsFilter(BaseFilter):
    async def __call__(self, event: Union[types.Message, types.CallbackQuery]) -> bool:
        user_id = event.from_user.id if isinstance(event, types.Message) else event.from_user.id
        return user_id in const.ADMINS

class CallbackStartsWithFilter(BaseFilter):
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix


    async def __call__(self, callback_query: types.CallbackQuery) -> bool:
        if not callback_query.data:
            return False
        return callback_query.data.startswith(self.prefix)

@router.callback_query(callbacks.ChoiceAdvPaginator.filter(F.reset_filter == True))
async def reset_filter(callback: types.CallbackQuery, callback_data: callbacks.ChoiceAdvPaginator,
                          bot: aiogram.Bot, state: FSMContext):

     wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
     await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
     await state.update_data(filter_advs=[])
     
     # Получаем список рекламных кампаний
     async with sm() as session:
         stmt = select(AdvSetting)\
             .join(AdvSetting.wb_cabinet)\
             .join(WBCabinet.wb_user_cabinets)\
             .where(WBUserCabinet.id == wb_user_cabinet_original_id)\
             .order_by(AdvSetting.name)
         result = await session.execute(stmt)
         adv_settings = result.scalars().all()
     
     message = messages.AdvCompanyChoicing(bot, callback.message.chat.id, wb_user_cabinet_original_id, adv_settings)
     message._page = 1
     message._state = state
     await message()
     return


@router.callback_query(F.data.startswith("wb_user_cabinet_page:"))
async def handle_pagination(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    # Разбираем callback_data
    _, wb_user_cabinet_original_id, page, *filter_parts = callback.data.split(":")
    wb_user_cabinet_original_id = int(wb_user_cabinet_original_id)
    page = int(page)
    keywords_filter = filter_parts[0].split(",") if filter_parts else None

    # Получаем список рекламных кампаний
    async with sm() as session:
        stmt = select(AdvSetting)\
            .join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)\
            .order_by(AdvSetting.name)
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()

    # Создаем и отправляем сообщение с новой страницей
    message = messages.AdvCompanyChoicing(
        bot,
        callback.message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings
    )
    message._page = page
    message._state = state
    await message()


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

    # Получаем список рекламных кампаний
    async with sm() as session:
        stmt = select(AdvSetting)\
            .join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)\
            .order_by(AdvSetting.name)
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()

    # Создаем и отправляем сообщение
    message = messages.AdvCompanyChoicing(
        bot,
        chat_id,
        wb_user_cabinet_original_id,
        adv_settings
    )
    message._page = page
    message._state = state
    await message()


@router.message(StateFilter(states.AdvCompanyCatalog.waiting_for_keywords_for_filter))
async def waiting_for_keywords_for_filter(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    text = message.text
    filter_advs = text.splitlines()
    filter_advs = [keyword.strip().lower() for keyword in filter_advs if keyword]
    await state.update_data(filter_advs=filter_advs)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data['last_wb_user_cabinet_original_id']
    page = 1

    # Получаем список рекламных кампаний
    async with sm() as session:
        stmt = select(AdvSetting)\
            .join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)\
            .order_by(AdvSetting.name)
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()

    # Создаем и отправляем сообщение
    message = messages.AdvCompanyChoicing(
        bot,
        chat_id,
        wb_user_cabinet_original_id,
        adv_settings
    )
    message._page = page
    message._state = state
    await message()


@router.callback_query(F.data.startswith("adv_setting_id:"))
async def handle_adv_setting_selection(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    # Разбираем callback_data
    _, adv_id = callback.data.split(":")
    adv_id = int(adv_id)

    await state.set_state(None)
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    
    # Получаем данные о рекламной кампании
    async with sm() as session:
        stmt = select(AdvSetting)\
            .where(AdvSetting.adv_id == adv_id)
        result = await session.execute(stmt)
        adv_setting = result.scalar()

        if not adv_setting:
            await bot.send_message(callback.message.chat.id, 'Кампания не найдена, попробуйте еще раз')
            return

        # Получаем wb_user_cabinet
        stmt = select(WBUserCabinet)\
            .join(WBUserCabinet.wb_cabinet)\
            .where(WBCabinet.id == adv_setting.wb_cabinet_id)
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalar()

    try:
        await messages.AdvSettingMenu(
            bot,
            callback.message.chat.id,
            wb_user_cabinet,
            adv_setting
        )()
    except NotItemsInAdvSetting:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)


@router.callback_query(callbacks.TurnBot.filter(F.action == 'on'))
async def turn_adv_on(callback: types.CallbackQuery, state: FSMContext,
                      callback_data: callbacks.TurnBot,
                      bot: aiogram.Bot):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=False) as session:
        session.begin()
        stmt = select(WBUserCabinet).join(WBUserCabinet.wb_cabinet)\
        .options(selectinload(WBUserCabinet.wb_cabinet))\
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = wb_user_cabinet.scalar()
        stmt = select(AdvSetting).options(selectinload(AdvSetting.payments))\
            .where(AdvSetting.id == adv_original_id)
        adv = await session.execute(stmt)
        adv: AdvSetting = adv.scalar()
        wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
        tariff_for_month = await pricer.get_price_for_day_for_shop(wb_cabinet.shop_id)
        PRICE_FOR_ADV_FOR_DAY = pricer.get_tariff_for_day(tariff_for_month)
        if wb_cabinet.expiration_time < datetime.now():
            if not (bonus := wb_cabinet.bonus):
                bonus = 0
            if not (balance := wb_cabinet.balance):
                balance = 0
            sum_balance = balance + bonus
            if not sum_balance >= PRICE_FOR_ADV_FOR_DAY:
                await bot.send_message(callback.message.chat.id, 'Недостаточно средств')
                await messages.ShopMenu(bot,
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
        await messages.AdvSettingMenu(bot,chat_id, wb_user_cabinet, adv)()
    return




@router.callback_query(callbacks.TurnBot.filter(F.action == 'off_all'))
async def turn_adv_off_all(callback: types.CallbackQuery, state: FSMContext,
                           callback_data: callbacks.TurnBot, bot: aiogram.Bot, ):
    await bot.send_message(callback.message.chat.id, 'Отключаю бота от всех кампаний')
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=False) as session:
        advs = await session.execute(select(AdvSetting).join(AdvSetting.wb_cabinet)\
        .join(WBCabinet.wb_user_cabinets)\
        .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        advs = advs.scalars().all()
        for adv in advs:
            adv.bot_active = False
        await session.commit()
    chat_id = callback.message.chat.id
    await messages.ShopMenu(bot,
                            chat_id,
                            state,
                            wb_user_cabinet_original_id)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == 'off'))
async def turn_adv_off(call: types.CallbackQuery, callback_data: callbacks.TurnBot, bot: aiogram.Bot, state: FSMContext):
    # data = await state.get_data()
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = select(WBUserCabinet).join(WBUserCabinet.wb_cabinet) \
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar()

    async with sm(read_only=False) as session:
        adv_setting = await session.execute(select(AdvSetting) \
                                            .where(AdvSetting.id == callback_data.adv_original_id))

        adv_setting: AdvSetting = adv_setting.scalars().first()
        adv_setting.bot_active = False
        await session.commit()

    await messages.AdvSettingMenu(call.bot,
                                  call.message.chat.id,
                                  wb_user_cabinet,
                                  adv_setting, )()


@router.callback_query(callbacks.ChangeAutoMinCTR.filter(F.action == 'turn_on_auto_min_ctr'))
async def turn_on_auto_min_ctr(callback: types.CallbackQuery,
                               bot: Bot,
                               callback_data: callbacks.ChangeAutoMinCTR,
                               state: FSMContext):
    adv_setting_original_id = callback_data.adv_setting_original_id
    stmt = update(AdvSetting) \
        .where(AdvSetting.id == callback_data.adv_setting_original_id) \
        .values({
        AdvSetting.new_auto_min_ctr_mode: True
    })

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
           .where(AdvSetting.id == adv_setting_original_id )\
    .values({
        AdvSetting.new_auto_min_ctr_mode : False
    })

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await messages.SettingMinCTR(bot,
                                 callback.message.chat.id)(adv_setting_original_id )

#
#
# @router.callback_query(callbacks.Min_ctr.filter(F.action == 'change'))
# async def change_min_ctr(callback: types.CallbackQuery,  callback_data: callbacks.Min_ctr,
#                          bot: aiogram.Bot, state: FSMContext, last_message:LastMessage):

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

@router.callback_query(CallbackStartsWithFilter('back_to_adv'), AdminsFilter())
async def back_to_advs(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    wb_user_cabinet_original_id = int(callback_query.data.split(':')[-1])
    
    # Получаем список рекламных кампаний
    async with sm() as session:
        stmt = select(AdvSetting)\
            .join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)\
            .order_by(AdvSetting.name)
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
    
    await messages.AdvCompanyChoicing(
        bot,
        callback_query.message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings,
        page=1
    )()

@router.callback_query(CallbackStartsWithFilter('cancel_delete_adv'), AdminsFilter())
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    wb_user_cabinet_original_id = int(callback_query.data.split(':')[-1])
    
    # Получаем список рекламных кампаний
    async with sm() as session:
        stmt = select(AdvSetting)\
            .join(AdvSetting.wb_cabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)\
            .order_by(AdvSetting.name)
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
        
    await messages.AdvCompanyChoicing(
        bot,
        callback_query.message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings,
        page=1
    )()
