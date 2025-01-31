from aiogram import Bot, Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, update
from app.client_bot.user_interface.handlers.start import start_registration
from app.client_bot import const
from app.client_bot.user_interface.views import callbacks
from app.utils.db.session_maker import get_async_session_maker as sm
from app import ao
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, AdvSetting
import logging

logger = logging.getLogger(__name__)

MAX_STEP = 1000

router = Router()

@router.callback_query(callbacks.CPMSettingMenu.filter(F.action=='change_cpm_step'))
async def change_cpm_step(callback: CallbackQuery,
                            callback_data: callbacks.CPMSettingMenu,
                            bot: Bot,
                            state: FSMContext):

    adv_original_id = callback_data.adv_original_id
    await state.update_data(adv_original_id=adv_original_id)
    user_telegram_id = callback.message.from_user.id
    await state.set_state('waiting_for_new_step')
    message = callback.message
    await message.answer(f'Введите новое значение шага ставки (до {MAX_STEP}):')


@router.message(StateFilter('waiting_for_new_step'))
async def set_new_step(message: Message,
                        state: FSMContext,
                        bot: Bot):
    data = await state.get_data()
    adv_original_id: int = data['adv_original_id']
    text = message.text
    if text == '/start':
        await state.set_state(None)
        await start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer('Введите целое положительное число')
        return
    new_step = int(text)
    if new_step < 1 or new_step > MAX_STEP:
        await message.answer(f'Введите целое положительное число от 1 до {MAX_STEP}')
        return
    async with sm(read_only=False) as session:
        query = update(AdvSetting)\
            .filter(AdvSetting.id == adv_original_id)\
        .values(bidder_step=new_step)
        await session.execute(query)
        await session.commit()
    await message.answer(f'Шаг ставки для изменен на {new_step}')
    await state.set_state(None)
    return





