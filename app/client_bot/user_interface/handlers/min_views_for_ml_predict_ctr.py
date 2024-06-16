import logging
from app.client_bot.user_interface.handlers import start
import aiogram
from aiogram import F, Router, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker
from .. import states

from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()

logger = logging.getLogger(__name__)



@router.callback_query(callbacks.ChangeMinViewsForPredictCTR.filter())
async def setting_min_views_for_predict_ctr(callback: types.CallbackQuery,
                                   bot: aiogram.Bot,
                                   state: FSMContext):
    await callback.answer()
    callback_data = await state.get_data()
    adv_original_id = callback_data['last_adv_original_id']
    await state.set_state(states.ChangeMinViewsForPredictCTR.waiting_for_new_min_views)
    await messages.SettingMinViewsForPredictCTR(bot, callback.message.chat.id)(adv_original_id)
    return

@router.message(StateFilter(states.ChangeMinViewsForPredictCTR.waiting_for_new_min_views))
async def set_min_views_for_predict_ctr(message: types.Message, bot: Bot, state: FSMContext):
    data = await state.get_data()
    adv_original_id = data['last_adv_original_id']
    text = message.text
    if '/start' in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    chat_id = message.chat.id

    def get_min_views_from_text(t: str):
        try:
            min_views = int(t)
            return min_views
        except ValueError:
            return None

    min_views = get_min_views_from_text(text)
    if min_views is not None:
        async with sm() as session:
            adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
            adv = adv.scalar()
            adv.min_views_for_ml_predict = min_views
            await session.commit()
            await messages.SettingMinViewsForPredictCTR(bot, chat_id)(adv_original_id)
            return
    async with sm() as session:
        adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
    await messages.IncorrectMinViewsForPredictCTR(bot, chat_id, adv)()
    return
