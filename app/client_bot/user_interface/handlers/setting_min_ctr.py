import logging

import aiogram
from aiogram import Bot, F, Router, types
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


@router.callback_query(callbacks.ChangeMinCTR.filter(F.action == "change_min_ctr"))
async def setting_min_ctr(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeMinCTR,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.ChangeMinCTR.waiting_for_new_min_ctr)
    assert callback.message is not None
    assert callback.message.chat is not None
    await messages.SettingMinCTR(bot, callback.message.chat.id)(adv_original_id)
    return


@router.message(StateFilter(states.ChangeMinCTR.waiting_for_new_min_ctr))
async def set_min_ctr(message: types.Message, bot: Bot, state: FSMContext) -> None:
    if message.text is None: return
    data = await state.get_data()
    adv_original_id = data["last_adv_original_id"]
    text = message.text
    if "/start" in text:
        await state.set_state(state=None)
        await start_registration(message, bot, state)
        return
    chat_id = message.chat.id

    def get_ctr_from_text(t: str) -> float | None:
        t = t.replace(",", ".")
        try:
            ctr_value = float(t.strip(" %")) / 100
            return ctr_value
        except ValueError:
            return None

    ctr = get_ctr_from_text(text)
    if ctr is not None:
        async with sm(read_only=False) as session:
            result_adv_setting = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
            adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
            if adv_setting is None: return
            adv_setting.hard_min_ctr = ctr # type: ignore
            await session.commit()
        assert message.chat is not None
        await messages.SettingMinCTR(bot, chat_id)(adv_original_id)
        return
    else:
        await message.answer("Некорректное значение, введите число от 0 до 100")
    return


# @router.callback_query(callbacks.ChangeMinCTR.filter(F.action == 'turn_on_auto_min_ctr'))
# async def turn_on_auto_min_ctr(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
#     data = await state.get_data()
#     adv_original_id = data['last_adv_original_id']
#     chat_id = callback.message.chat.id
#     async with sm(read_only=False) as session:
#         adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
#         adv = adv.scalar()
#         adv.hard_min_ctr = None
#         await session.commit()
#     await messages.SettingMinCTR(bot,
#                                  chat_id)(adv_original_id)
#     return
