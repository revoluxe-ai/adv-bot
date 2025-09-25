import logging

import aiogram
from aiogram import Bot, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.client_bot.user_interface.handlers.start_registration_func import start_registration
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

from .. import states
from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()

logger = logging.getLogger(__name__)


@router.callback_query(callbacks.ChangeMinViewsForPredictCTR.filter())
async def setting_min_views_for_predict_ctr(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeMinViewsForPredictCTR,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    adv_original_id = callback_data.adv_setting_original_id
    await state.set_state(states.ChangeMinViewsForPredictCTR.waiting_for_new_min_views)
    assert callback.message is not None
    assert callback.message.chat is not None
    await messages.SettingMinViewsForPredictCTR(bot, callback.message.chat.id)(adv_original_id)
    return


@router.message(StateFilter(states.ChangeMinViewsForPredictCTR.waiting_for_new_min_views))
async def set_min_views_for_ml_predict_ctr(
    message: types.Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    adv_original_id = data["last_adv_original_id"]
    text = message.text
    if text is not None and "/start" in text:
        await state.set_state(state=None)
        await start_registration(message, bot, state)
        return
    assert message.chat is not None
    chat_id = message.chat.id

    def get_min_views_from_text(t: str) -> int | None:
        try:
            min_views_int = int(t)
            return min_views_int
        except ValueError:
            return None

    if text is None:
        assert message.chat is not None
        await message.answer("Введите целое положительное число")
        return
    min_views = get_min_views_from_text(text)
    if min_views is not None:
        async with sm(read_only=False) as session:
            result_adv_setting = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
            adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
            if adv_setting is None: return
            adv_setting.min_views_for_ml_predict = min_views
            await session.commit()
            assert message.chat is not None
            await messages.SettingMinViewsForPredictCTR(bot, chat_id)(adv_original_id)
            return
    async with sm() as session:
        result_adv_setting = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        adv_setting_for_incorrect_message: AdvSetting | None = result_adv_setting.scalar_one_or_none()
    if adv_setting_for_incorrect_message is None: return # Заглушка, если adv_setting все еще None
    assert message.chat is not None
    await messages.IncorrectMinViewsForPredictCTR(bot, chat_id, adv_setting_for_incorrect_message)()
    return
