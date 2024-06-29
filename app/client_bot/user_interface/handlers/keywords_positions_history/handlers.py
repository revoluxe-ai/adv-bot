from typing import Union

import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import logging
from app.client_bot import utils
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBCategory,
    WBUserCabinet,
)
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.utils import redis_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.client_bot.user_interface.views import messages, callbacks
from app.client_bot.user_interface import states

logger = logging.getLogger(__name__)

router = Router()


_sm = get_async_session_maker



@router.callback_query(callbacks.KeywordPositionHistory.filter())
async def keyword_position_history(callback: types.CallbackQuery,
                                   callback_data: callbacks.KeywordPositionHistory,
                                   bot: aiogram.Bot,
                                   state: FSMContext):
    await callback.answer()
    await state.set_state(state = None)
    adv_original_id: int = callback_data.adv_original_id
    await callback.answer()
    try:
          graphic, legend = (await utils.get_keyword_history_graphic(adv_original_id))
    except Exception as e:
        logger.error(e, exc_info=True)
        await messages.NotKeywordHistoryPositions(bot, callback.message.chat.id)()
        return
    if legend:
        await messages.KeywordGraphicPart_1(bot, callback.message.chat.id, graphic, adv_original_id)()
        await messages.KeywordGraphicPart_2(bot, callback.message.chat.id, legend, adv_original_id)()
    else:
        await messages.KeywordGraphicPart_2(bot, callback.message.chat.id, graphic, adv_original_id)()


