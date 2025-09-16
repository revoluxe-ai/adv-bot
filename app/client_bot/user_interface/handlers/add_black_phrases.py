from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.utils.db.session_maker import get_async_session_maker as sm

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
async def waiting_for_black_phrases(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    text = message.text
    if not text:
        return None
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        adv: AdvSetting = await session.get(AdvSetting, adv_setting_id)

    rel_manager = RelevantPhraseManager(adv)
    await rel_manager.update_black_phrases(keywords)
    assert message.from_user
    user_id = message.from_user.id
    await messages.WaitingForBlackPhrases(bot, user_id)(adv_setting_id)
    return None


@router.callback_query(callbacks.ResetBlackPhrases.filter())
async def reset_black_phrases(
    callback: CallbackQuery, bot: Bot, callback_data: callbacks.ResetBlackPhrases
) -> None:

    adv_setting_original_id = callback_data.adv_setting_id
    async with sm(read_only=True) as session:
        adv: AdvSetting | None = await session.get(AdvSetting, adv_setting_original_id)
        if not adv:
            raise
    manager = RelevantPhraseManager(adv)
    await manager.update_black_phrases([])
    await messages.WaitingForBlackPhrases(bot, callback.from_user.id)(
        callback_data.adv_setting_id
    )
