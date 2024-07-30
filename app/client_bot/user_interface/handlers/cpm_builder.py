import logging
import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from . import start
from .. import states
from ..views import callbacks, messages
sm = get_async_session_maker

router = Router()


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == 'to_cpm_setting_page'))
async def to_page_for_cpm_setting(callback: types.CallbackQuery,
                               callback_data: callbacks.ChoiceAdvPaginator,
                               bot: aiogram.Bot,
                               ):

    await callback.answer()
    adv_original_id = callback_data.adv_original_id
    await messages.CPMSetting(bot, callback.message.chat.id)(adv_original_id)
    return


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == 'set_auto_cpm'))
async def get_min_position(callback: types.CallbackQuery,
                                 callback_data: callbacks.ChoiceAdvPaginator,
                                 bot: aiogram.Bot,
                                 state: FSMContext):

     await callback.answer()
     adv_original_id = callback_data.adv_original_id
     await state.update_data(last_adv_original_id=adv_original_id)
     await state.set_state(states.CPMSetting.waiting_for_min_position)
     await messages.AutoCPMSettingGetMinPosition(bot,callback.message.chat.id)(adv_original_id)
     return

@router.message(StateFilter(states.CPMSetting.waiting_for_min_position))
async def get_max_cpm(message: types.Message, bot: aiogram.Bot, state: FSMContext):

    text = message.text
    if '/start' in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer('Введите целое положительное число')
        return
    min_position = int(text)
    if min_position < 1:
        await message.answer('Введите целое положительное число от 1 и выше')
        return
    await state.update_data(min_position=min_position)
    await state.set_state(states.CPMSetting.waiting_for_max_cpm)
    await messages.AutoCPMSettingGetMaxCPM(bot, message.chat.id)()
    return


@router.message(StateFilter(states.CPMSetting.waiting_for_max_cpm))
async def set_max_cpm(message: types.Message, bot: aiogram.Bot, state: FSMContext):
    data = await state.get_data()
    text = message.text
    if '/start' in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer('Введите целое положительное число')
        return
    max_cpm = int(text)
    if max_cpm < 1:
        await message.answer('Введите целое положительное число от 1 и выше')
        return

    state_data = await state.get_data()
    adv_original_id = state_data['last_adv_original_id']
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
        adv.max_place = data['min_position']
        adv.max_cpm = max_cpm
        adv.bidder_active = True
        await session.commit()
        await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
    await state.set_state(state=None)
    return



@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == 'set_manual_cpm'))
async def set_manual_cpm(callback: types.CallbackQuery,
                                 callback_data: callbacks.ChoiceAdvPaginator,
                                 bot: aiogram.Bot,
                                 state: FSMContext):

    await callback.answer()
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.CPMSetting.waiting_for_manual_cpm)
    await messages.ManualCPMSetting(bot, callback.message.chat.id)()
    return


@router.message(StateFilter(states.CPMSetting.waiting_for_manual_cpm))
async def set_manual_cpm(message: types.Message, bot: aiogram.Bot, state: FSMContext):
    text = message.text
    if '/start' in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer('Введите целое положительное число')
        return
    manual_cpm = int(text)
    if manual_cpm < 125:
        await message.answer('Введите целое положительное число от 150 и выше')
        return
    state_data = await state.get_data()
    adv_original_id = state_data['last_adv_original_id']

    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
        adv.max_cpm = manual_cpm
        adv.bidder_active = False
        await session.commit()
    async with sm() as session:
        stmt = select(WBUserCabinet)\
            .join(WBUserCabinet.wb_cabinet)\
            .join(WBCabinet.adv_settings)\
            .options(selectinload(WBUserCabinet.user))\
            .where(
            AdvSetting.id == adv_original_id,
            User.user_telegram_id == message.from_user.id
        )
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalar()
    access = await super_cabinet_manager.get_access_for_wb_user_cabinet(wb_user_cabinet)

    api = WBApi(access)
    await api.advert.update_cpm(adv.adv_id, manual_cpm)

    await bot.send_message(message.chat.id, f'CPM успешно установлен ({manual_cpm}) р.')
    await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
    await state.set_state(state=None)
    return


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == 'set_max_position'))
async def set_max_position(callback: types.CallbackQuery,
                                    callback_data: callbacks.ChoiceAdvPaginator,
                                    bot: aiogram.Bot,
                                    state: FSMContext):

        await callback.answer()
        adv_original_id = callback_data.adv_original_id
        await state.update_data(last_adv_original_id=adv_original_id)
        await state.set_state(states.CPMSetting.waiting_for_max_position)
        await messages.AutoCPMSettingGetMinPosition(bot, callback.message.chat.id)(adv_original_id)
        return


@router.message(StateFilter(states.CPMSetting.waiting_for_max_position))
async def set_max_position(message: types.Message, bot: aiogram.Bot, state: FSMContext):
    text = message.text
    if '/start' in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer('Введите целое положительное число')
        return
    max_position = int(text)
    if max_position < 1:
        await message.answer('Введите целое положительное число от 1 и выше')
        return
    state_data = await state.get_data()
    adv_original_id = state_data['last_adv_original_id']
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
        adv.max_place = max_position
        await session.commit()
        await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
    await state.set_state(state=None)
    return