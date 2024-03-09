import asyncio
import aiogram
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import selectinload, joinedload
from app.telegram_bot.models import User
from app.db.associations import WBUserCabinet
from app.wildberries.models import WBCabinet, AdvSetting
import app
from sqlalchemy.future import select
from session_maker import get_async_session_maker
from ..views import messages
from app.my_types import LastMessage
from ..views import callbacks
from ..views.callbacks import Action
from .. import states
from ...redis_manager import RedisManager
router = Router()
from app.telegram_bot.wb_user_cabinet_manager import CabinetManager



sm = get_async_session_maker()


redis_manager = RedisManager()



@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(callback: types.CallbackQuery,
                               callback_data: callbacks.ChoiceAdvPaginator,
                               bot: aiogram.Bot,
                              last_message:LastMessage):
    if callback.id != 'fake_id':
        await callback.answer()
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    page = callback_data.page
    async with sm() as session:
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.wb_cabinet)  # Явно указываем соединение с WBCabinet
            .options(
                selectinload(WBUserCabinet.wb_cabinet).\
                    selectinload(WBCabinet.adv_settings),  # Загружаем adv_settings
                selectinload(WBUserCabinet.user)  # Загружаем информацию о пользователе
            )
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)  # Условие должно быть скорректировано
        )
        result = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result.scalars().first()
        if not wb_user_cabinet.wb_cabinet.adv_settings:
            adv_settings_stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_user_cabinet.wb_cabinet.id)
            adv_settings_result = await session.execute(adv_settings_stmt)
            wb_user_cabinet.wb_cabinet.adv_settings = adv_settings_result.scalars().all()
        if page == 1:
            user_cabinet_manager = CabinetManager(wb_user_cabinet)
            await user_cabinet_manager.update_all_data()
        await session.refresh(wb_user_cabinet)

        last_message, message_type = await messages.AdvCompanyChoicing\
            (bot, last_message, callback.message.chat.id, wb_user_cabinet, page=page)()

        return last_message, message_type


@router.callback_query(callbacks.Adv.filter())
async def adv(callback: types.CallbackQuery,  callback_data: callbacks.Adv,
               bot: aiogram.Bot, last_message:LastMessage):
    await bot.answer_callback_query(callback.id)
    adv_original_id = callback_data.adv_original_id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
        wb_user_cabinet = await session.execute(select(WBUserCabinet)\
                    .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        wb_user_cabinet = wb_user_cabinet.scalar()
    last_message, message_type = await messages.AdvSettingMenu(bot, last_message,
                                                               wb_user_cabinet,
                                                               adv,
                                                               callback.message.chat.id)()
    return last_message, message_type


@router.callback_query(callbacks.TurnAdv.filter(F.action == 'on'))
async def turn_adv_on(callback: types.CallbackQuery, state: FSMContext,
                      callback_data: callbacks.TurnAdv,
                      bot: aiogram.Bot, last_message:LastMessage):
    await callback.answer('Включаю бота')
    adv_id = callback_data.adv_original_id
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
        adv: AdvSetting = adv.scalar()
        adv.bot_active = True
        await session.commit()
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.ChangeMinCTR.min_ctr)
    await state.update_data(adv_original_id=adv_id)
    last_message, message_type = await messages.GetMinCtr(bot, last_message,
                                                           callback.message.chat.id, adv)()
    return last_message, message_type


@router.message(StateFilter(states.ChangeMinCTR.min_ctr))
async def change_min_ctr(message: types.Message, state: FSMContext, bot: aiogram.Bot, last_message:LastMessage):
    min_ctr = message.text
    if not min_ctr.isdigit():
        last_message, message_type = (messages.\
            WrongMinCTR(bot, last_message, message.chat.id)())
        return last_message, message_type
    min_ctr = int(min_ctr)
    if 0 > min_ctr > 100:
        last_message, message_type = (messages.\
            WrongMinCTR(bot, last_message, message.chat.id)())
        return last_message, message_type
    async with sm() as session:
        data = await state.get_data()
        adv_original_id = data['adv_original_id']
        adv = await session.execute(select(AdvSetting)\
                                    .where(AdvSetting.id == adv_original_id))
        adv: AdvSetting = adv.scalar()
        adv.min_ctr = min_ctr
        wb_user_cabinet = await session.execute(select(WBUserCabinet)\
                    .where(WBUserCabinet.id == data['wb_user_cabinet_original_id']))
        wb_user_cabinet = wb_user_cabinet.scalar()
        await session.commit()
    await state.clear()
    last_message, message_type = await messages.\
        MinCTRChanged(bot, last_message, message.chat.id)()
    await redis_manager.set_last_message(last_message, message_type)
    await state.clear()
    last_message, message_type = await messages.AdvSettingMenu(bot, last_message,
                                                wb_user_cabinet,
                                                adv, message.chat.id)()

    return last_message, message_type


