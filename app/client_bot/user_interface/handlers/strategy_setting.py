import logging

import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()

logger = logging.getLogger(__name__)


@router.callback_query(callbacks.StrategySetting.filter(F.action == "turn_on_min_ctr"))
async def turn_on_min_ctr(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.StrategySetting,
    state: FSMContext,
):
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv: AdvSetting = adv.scalar()
        adv.target_ctr_mode = False
        await session.commit()

    await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
    return


@router.callback_query(callbacks.StrategySetting.filter(F.action == "on_target_ctr"))
async def on_target_ctr(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.StrategySetting,
    state: FSMContext,
):
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv: AdvSetting = adv.scalar()
        adv.target_ctr_mode = True
        await session.commit()
    await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
    return


@router.callback_query(
    callbacks.StrategySetting.filter(F.action == "turn_on_forward_mode")
)
async def turn_on_forward_mode(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.StrategySetting,
    state: FSMContext,
):
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv: AdvSetting = adv.scalar()
        adv.target_ctr_mode_strategy = "forward"
        await session.commit()
    await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
    return


@router.callback_query(
    callbacks.StrategySetting.filter(F.action == "turn_on_keep_mode")
)
async def turn_on_keep_mode(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.StrategySetting,
    state: FSMContext,
):
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv: AdvSetting = adv.scalar()
        adv.target_ctr_mode_strategy = "keep"
        await session.commit()
    await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
    return


@router.callback_query(callbacks.StrategySetting.filter())
async def strategy_setting(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.StrategySetting,
    state: FSMContext,
):
    adv_original_id = callback_data.adv_setting_original_id
    await messages.StrategySetting(bot, callback.message.chat.id)(adv_original_id)
    return
