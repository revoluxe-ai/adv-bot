from aiogram import Router, Bot
from aiogram.filters.callback_data import CallbackData
import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker
sm = get_async_session_maker

router = Router()

from app.client_bot.user_interface.views import callbacks


@router.callback_query(callbacks.ResetPlace.filter(F.action=='on'))
async def on_reset_place( callback: types.CallbackQuery,
                               callback_data: callbacks.ResetPlace,
bot: Bot,
                               ):

    adv_original_id: int = callback_data.adv_setting_original_id
    async with sm() as session:
        async with session.begin():
            adv_setting = await session.execute(select(AdvSetting)\
                                                .where(AdvSetting.id == adv_original_id))
            adv_setting = adv_setting.scalars().first()
            adv_setting.place = False
            await session.commit()
    await bot.send_message(callback.message.chat.id, 'Сброс места включен')


@router.callback_query(callbacks.ResetPlace.filter(F.action=='off'))
async def off_reset_place(
                          callback: types.CallbackQuery,
                           callback_data: callbacks.ResetPlace,
                            bot: aiogram.Bot,

                               ):

    adv_original_id: int = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv_setting = await session.execute(select(AdvSetting)\
                                            .where(AdvSetting.id == adv_original_id))
        adv_setting: AdvSetting = adv_setting.scalars().first()
        adv_setting.reset_place = False
        await session.commit()
    await bot.send_message(callback.message.chat.id, 'Сброс места выключен')


