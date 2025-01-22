from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.utils.db.session_maker import get_async_session_maker as sm
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import WBCabinet, AdvSetting

router = Router()


@router.callback_query(callbacks.TurnWhiteListUpdate.filter(F.action == 'on'))
async def turn_white_list_update_on(callback_query: CallbackQuery,
                                    callback_data: callbacks.TurnWhiteListUpdate,
                                    bot: Bot,):


    async with sm(read_only=False) as session:
        stmt = select(WBCabinet)\
            .join(WBCabinet.adv_settings)\
            .options(selectinload(WBCabinet.adv_settings))\
            .filter(WBCabinet.id == callback_data.wb_cabinet_original_id)
        wb_cabinet = await session.execute(stmt)
        wb_cabinet = wb_cabinet.scalar()
        adv_settings: list[AdvSetting] = wb_cabinet.adv_settings
        for adv in adv_settings:
            adv.new_auto_min_ctr_mode = True
        wb_cabinet.white_list_update_active = True
        await session.commit()
    chat_id = callback_query.message.chat.id
    await bot.send_message(chat_id, 'Автодобавление белого первого ключа в белый список включено')




@router.callback_query(callbacks.TurnWhiteListUpdate.filter(F.action == 'off'))
async def turn_white_list_update_off(callback_query: CallbackQuery,
                                     callback_data: callbacks.TurnWhiteListUpdate,
                                     bot: Bot,):
    async with sm(read_only=False) as session:
        stmt = select(WBCabinet)\
            .filter(WBCabinet.id == callback_data.wb_cabinet_original_id)
        wb_cabinet = await session.execute(stmt)
        wb_cabinet = wb_cabinet.scalar()
        wb_cabinet.white_list_update_active = False
        await session.commit()
    chat_id = callback_query.message.chat.id
    await bot.send_message(chat_id, 'Автодобавление белого первого ключа в белый список выключено')
