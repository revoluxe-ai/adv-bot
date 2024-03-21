import logging
import aiogram
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.modules.common_slaves.wildberries.models import WBUserCabinet,  WBCabinet, AdvSetting
from sqlalchemy.future import select
from app.utils.db.session_maker import get_async_session_maker
from ..views import messages
from ..views import callbacks
from ...redis_manager import RedisManager

sm = get_async_session_maker()

router = Router()


logger = logging.getLogger(__name__)


@router.callback_query(callbacks.Adv.filter(F.action == 'new'))
async def pr
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

    # if page == 1:
    #     user_cabinet_manager = await get_cabinet_manager(wb_user_cabinet_original_id)
    #     await user_cabinet_manager.update_all_data()
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

