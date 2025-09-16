import aiogram
from aiogram import Bot, F, Router, types

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker
from sqlalchemy import update

router = Router()

from app.client_bot.user_interface.views import callbacks


@router.callback_query(callbacks.ResetPlace.filter(F.action=='on'))
async def on_reset_place( callback: types.CallbackQuery,
                               callback_data: callbacks.ResetPlace,
                                bot: Bot,
                               ):

    adv_original_id: int = callback_data.adv_setting_original_id

    stmt = update(AdvSetting)\
        .filter(AdvSetting.id == adv_original_id)\
    .values(reset_place = True)

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await bot.send_message(callback.message.chat.id, 'Сброс места включен')


@router.callback_query(callbacks.ResetPlace.filter(F.action=='off'))
async def off_reset_place(
                          callback: types.CallbackQuery,
                           callback_data: callbacks.ResetPlace,
                            bot: aiogram.Bot,

                               ):
    adv_original_id: int = callback_data.adv_setting_original_id

    stmt = update(AdvSetting) \
        .filter(AdvSetting.id == adv_original_id) \
        .values(reset_place = False)

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await bot.send_message(callback.message.chat.id, 'Сброс места выключен')


