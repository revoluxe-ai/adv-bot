import logging
import aiogram
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import joinedload
from app.db.associations import WBUserCabinet
from app.wildberries.models import WBCabinet, AdvSetting
from sqlalchemy.future import select
from app.session_maker import get_async_session_maker
from ..views import messages
from app.my_types import LastMessage
from ..views import callbacks
from ...redis_manager import RedisManager

from app.telegram_bot.wb_user_cabinet_manager import get_cabinet_manager

sm = get_async_session_maker()

router = Router()
redis_manager = RedisManager()
logger = logging.getLogger(__name__)


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(callback: types.CallbackQuery,
                               callback_data: callbacks.ChoiceAdvPaginator,
                               bot: aiogram.Bot,
                               state: FSMContext):

    await bot.answer_callback_query(callback_query_id=callback.id)
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    page = callback_data.page
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.update_data(wb_user_cabinet_page=page)
    check_data = await state.get_data()
    logger.debug(f'check_data: {check_data}')

    if page == 1:
        user_cabinet_manager = await get_cabinet_manager(wb_user_cabinet_original_id)
        await user_cabinet_manager.update_all_data()
    async with (sm() as session):
        stmt = select(AdvSetting)\
        .join(AdvSetting.wb_cabinet)\
        .join(WBCabinet.wb_user_cabinets)\
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()


    chat_id = callback.message.chat.id

    await messages.AdvCompanyChoicing \
        (bot, chat_id, wb_user_cabinet_original_id, adv_settings, page=page)()

    return


@router.callback_query(callbacks.Adv.filter())
async def adv(callback: types.CallbackQuery, callback_data: callbacks.Adv,
              bot: aiogram.Bot):
    await bot.answer_callback_query(callback.id)
    adv_original_id = callback_data.adv_original_id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
        wb_user_cabinet = await session.execute(select(WBUserCabinet) \
                                                .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        wb_user_cabinet = wb_user_cabinet.scalar()
    chat_id = callback.message.chat.id
    await messages.AdvSettingMenu(bot,
                                                               chat_id,
                                                               wb_user_cabinet,
                                                               adv,
                                                               )()
    return

# @router.message(StateFilter(states.ChangeMinCTR.min_ctr))
# async def change_min_ctr(message: types.Message, state: FSMContext, bot: aiogram.Bot, last_message:LastMessage):
#     min_ctr = message.text
#     if not min_ctr.isdigit():
#         last_message, message_type = messages.\
#             WrongMinCTR(bot, last_message, message.chat.id)()
#         return last_message, message_type
#     min_ctr = int(min_ctr)
#     if 0 > min_ctr > 100:
#         last_message, message_type = (messages.\
#             WrongMinCTR(bot, last_message, message.chat.id)())
#         return last_message, message_type
#     async with sm() as session:
#         data = await state.get_data()
#         adv_original_id = data['adv_original_id']
#         adv = await session.execute(select(AdvSetting)\
#                                     .where(AdvSetting.id == adv_original_id))
#         adv: AdvSetting = adv.scalar()
#         adv.min_ctr = min_ctr/100
#         wb_user_cabinet = await session.execute(select(WBUserCabinet)\
#                     .where(WBUserCabinet.id == data['wb_user_cabinet_original_id']))
#         wb_user_cabinet = wb_user_cabinet.scalar()
#         await session.commit()
#     await state.clear()
#     last_message, message_type = await messages.\
#         MinCTRChanged(bot, last_message, message.chat.id)()
#     await redis_manager.set_last_message(last_message, message_type)
#     await state.clear()
#     last_message, message_type = await messages.AdvSettingMenu(bot, last_message,
#                                                 wb_user_cabinet,
#                                                 adv, message.chat.id)()
#
#     return last_message, message_type


@router.callback_query(callbacks.TurnAdv.filter(F.action == 'on'))
async def turn_adv_on(callback: types.CallbackQuery, state: FSMContext,
                      callback_data: callbacks.TurnAdv,
                      bot: aiogram.Bot):
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
async def turn_adv_off(callback: types.CallbackQuery, callback_data: callbacks.TurnAdv, bot: aiogram.Bot,
                       last_message: LastMessage):
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
