from aiogram import Router, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.wb_adv_updater import data_manager

router = Router()


@router.callback_query(callbacks.AddBlackPhrasesTemplates.filter())
async def add_white_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddWhitePhrases,
    state: FSMContext,
) -> None:

    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddBlackPhrasesTemplates.waiting_for_black_phrases)
    await messages.WaitingForBlackPhrases(
        bot,
        callback.from_user.id,
    )(adv_setting_id)


@router.message(StateFilter(states.AddBlackPhrasesTemplates.waiting_for_black_phrases))
async def waiting_for_black_phrases(message, bot: Bot, state: FSMContext) -> None:
    text = message.text
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    await data_manager.update_black_phrases(adv_setting_id, keywords)
    user_id = message.from_user.id
    await messages.WaitingForBlackPhrases(bot, user_id)(adv_setting_id)


@router.callback_query(callbacks.ResetBlackPhrases.filter())
async def reset_black_phrases(
    callback: CallbackQuery, bot: Bot, callback_data: callbacks.ResetBlackPhrases
) -> None:

    await data_manager.reset_black_phrases(callback_data.adv_setting_id)
    await messages.WaitingForBlackPhrases(bot, callback.from_user.id)(
        callback_data.adv_setting_id
    )
