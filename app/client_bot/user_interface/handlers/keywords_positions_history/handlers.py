import logging

import aiogram
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.client_bot.user_interface.views import messages, callbacks
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
)
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker
from app.utils.graphic_positions_creator import get_keyword_history_graphic

logger = logging.getLogger(__name__)

router = Router()


_sm = get_async_session_maker


@router.callback_query(callbacks.KeywordPositionHistory.filter())
async def keyword_position_history(
    callback: types.CallbackQuery,
    callback_data: callbacks.KeywordPositionHistory,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    await state.set_state(state=None)
    adv_original_id: int = callback_data.adv_original_id

    stmt = select(AdvSetting).filter(AdvSetting.id == adv_original_id)

    async with _sm() as session:
        result = await session.execute(stmt)
        adv: AdvSetting = result.scalar_one()
    keywords = await data_manager.get_good_bad_phrases(adv)

    result = await get_keyword_history_graphic(adv_original_id, keywords)
    if not result:
        await messages.NotKeywordHistoryPositions(bot, callback.message.chat.id)()
        return
    graphic, legend = result
    if legend:
        await messages.KeywordGraphicPart_1(
            bot, callback.message.chat.id, graphic, adv_original_id
        )()
        await messages.KeywordGraphicPart_2(
            bot, callback.message.chat.id, legend, adv_original_id
        )()
    else:
        await messages.KeywordGraphicPart_2(
            bot, callback.message.chat.id, graphic, adv_original_id
        )()
