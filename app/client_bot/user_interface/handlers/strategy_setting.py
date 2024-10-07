


import asyncio
import logging

from sqlalchemy.orm import selectinload

from app.client_bot.user_interface.handlers import start
import aiogram
from aiogram import F, Router, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.modules.wb_adv_updater import wb_manager
from app.modules.wb_adv_updater.data_setter import DataSetter
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker
from .. import states

from ..views import callbacks, messages
from app.exc import ApiForbiddenError

sm = get_async_session_maker

router = Router()

logger = logging.getLogger(__name__)



@router.callback_query(callbacks.StrategySetting.filter(F.action == 'turn_on_min_ctr'))
async def turn_on_min_ctr(callback: types.CallbackQuery,
                            bot: aiogram.Bot,
                            callback_data: callbacks.StrategySetting,
                            state: FSMContext):
     await callback.answer()
     adv_original_id = callback_data.adv_setting_original_id
     async with sm() as session:
          adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
          adv: AdvSetting = adv.scalar()
          adv.target_ctr_mode = False
          await session.commit()

     await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
     return


@router.callback_query(callbacks.StrategySetting.filter(F.action == 'on_target_ctr'))
async def on_target_ctr(callback: types.CallbackQuery,
                            bot: aiogram.Bot,
                            callback_data: callbacks.StrategySetting,
                            state: FSMContext):
     await callback.answer()
     adv_original_id = callback_data.adv_setting_original_id
     async with sm() as session:
          adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
          adv: AdvSetting = adv.scalar()
          adv.target_ctr_mode = True
          await session.commit()
     await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
     return




@router.callback_query(callbacks.StrategySetting.filter(F.action == 'turn_on_forward_mode'))
async def turn_on_forward_mode(callback: types.CallbackQuery,
                            bot: aiogram.Bot,
                            callback_data: callbacks.StrategySetting,
                            state: FSMContext):
     await callback.answer()
     adv_original_id = callback_data.adv_setting_original_id
     async with sm() as session:
          adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
          adv: AdvSetting = adv.scalar()
          adv.target_ctr_mode_strategy = 'forward'
          await session.commit()
     await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
     return


@router.callback_query(callbacks.StrategySetting.filter(F.action == 'turn_on_keep_mode'))
async def turn_on_keep_mode(callback: types.CallbackQuery,
                            bot: aiogram.Bot,
                            callback_data: callbacks.StrategySetting,
                            state: FSMContext):
     await callback.answer()
     adv_original_id = callback_data.adv_setting_original_id
     async with sm() as session:
          adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
          adv: AdvSetting = adv.scalar()
          adv.target_ctr_mode_strategy = 'keep'
          await session.commit()
     await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
     return




@router.callback_query(callbacks.StrategySetting.filter())
async def strategy_setting(callback: types.CallbackQuery,
                           bot: aiogram.Bot,
                           callback_data: callbacks.StrategySetting,
                            state: FSMContext):

    await callback.answer()
    adv_original_id = callback_data.adv_setting_original_id
    await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
    return




