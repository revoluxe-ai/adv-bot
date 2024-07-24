from aiogram import Router, Bot
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers.start import start_registration
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.wb_adv_updater import data_manager

router = Router()


@router.callback_query(callbacks.AddWhitePhrases.filter())
async def add_white_phrases(callback: CallbackQuery,
                            bot: Bot,
                            callback_data: callbacks.AddWhitePhrases,
                            state: FSMContext):
    await callback.answer('Добавление фраз в белый список')
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddWhitePhrases.waiting_for_white_phrases)
    await messages.WaitingForWhitePhrases(bot, callback.from_user.id, )(adv_setting_id)


@router.message(StateFilter(states.AddWhitePhrases.waiting_for_white_phrases))
async def waiting_for_white_phrases(message, bot: Bot, state: FSMContext):
    text = message.text
    if '/start' in text:
        await start_registration(message, bot, state)
        return
    keywords = text.split('\n')
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data['last_adv_setting_id']
    await data_manager.add_white_phrases(keywords, adv_setting_id)
    await messages.WhitePhrasesAdded(bot, message.from_user.id)(adv_setting_id)