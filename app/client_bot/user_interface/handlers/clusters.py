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


@router.callback_query(callbacks.TurnClusters.filter(F.action == 'on'))
async def turn_clusters_on(callback: types.CallbackQuery, bot: Bot,
                           state: FSMContext, callback_data: callbacks.TurnClusters):
    adv_setting_id = callback_data.adv_original_id
    data = await state.get_data()

    async with sm() as session:
        adv_setting = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_id)
        )
        adv_setting: AdvSetting = adv_setting.scalar()
        adv_setting.clusters_mode = True
        await session.commit()
    wb_user_cabinet_original_id = data['last_wb_user_cabinet_original_id']
    async with sm() as session:
        wb_user_cabinet = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet: WBUserCabinet = wb_user_cabinet.scalar()
    chat_id = callback.message.chat.id
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.TurnClusters.filter(F.action == 'off'))
async def turn_clusters_off(callback: types.CallbackQuery, bot: Bot,
                            state: FSMContext, callback_data: callbacks.TurnClusters):
    adv_setting_id = callback_data.adv_original_id
    data = await state.get_data()

    async with sm() as session:
        adv_setting = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_id)
        )
        adv_setting: AdvSetting = adv_setting.scalar()
        adv_setting.clusters_mode = False
        await session.commit()
    wb_user_cabinet_original_id = data['last_wb_user_cabinet_original_id']
    async with sm() as session:
        wb_user_cabinet = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet: WBUserCabinet = wb_user_cabinet.scalar()
    chat_id = callback.message.chat.id
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()