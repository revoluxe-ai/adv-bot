from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select
import aiogram

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting, WBUserCabinet
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from typing import cast

router = Router()


@router.callback_query(callbacks.AddWhitePhrases.filter())
async def add_white_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddWhitePhrases,
    state: FSMContext,
) -> None:
    if callback.from_user is None:
        return
    user_telegram_id = callback.from_user.id
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddWhitePhrases.waiting_for_white_phrases)
    await messages.WaitingForWhitePhrases(
        bot,
        user_telegram_id,  # type: ignore
    )(adv_setting_id)


@router.message(StateFilter(states.AddWhitePhrases.waiting_for_white_phrases))
async def waiting_for_white_phrases(message: aiogram.types.Message, bot: Bot, state: FSMContext) -> None:
    if message.text is None:
        return
    text = message.text
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    await data_manager.add_white_phrases(keywords, adv_setting_id)
    await messages.WhitePhrasesAdded(bot, message.from_user.id)(adv_setting_id)


@router.callback_query(callbacks.AddRelevantPhrases.filter())
async def add_relevant_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddRelevantPhrases,
    state: FSMContext,
) -> None:
    if callback.from_user is None:
        return
    user_telegram_id = callback.from_user.id
    await callback.answer("Добавление фраз в релевантный список")
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddRelevantPhrases.waiting_for_relevant_phrases)
    await messages.WaitingForRelevantPhrases(bot, user_telegram_id)  # type: ignore


@router.message(StateFilter(states.AddRelevantPhrases.waiting_for_relevant_phrases))
async def waiting_for_relevant_phrases(message: aiogram.types.Message, bot: Bot, state: FSMContext) -> None:
    if message.text is None:
        return
    text = message.text
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    await messages.LongTimeOperation(bot, message.from_user.id)()
    assert message.from_user is not None
    await data_manager.add_relevant_phrases(keywords, adv_setting_id)
    await messages.RelevantPhrasesAdded(bot, message.from_user.id, adv_setting_id)()


@router.callback_query(callbacks.ResetWhiteList.filter())
async def reset_white_list(
    callback: CallbackQuery,
    bot: Bot,  # оставь bot ключевым аргументом
    state: FSMContext,
    callback_data: callbacks.ResetWhiteList,
) -> None:
    if callback.from_user is None:
        return
    user_telegram_id = callback.from_user.id
    await bot.send_message(user_telegram_id, "Сброс белого списка...")
    adv_setting_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id,
            KeywordSetting.hard_status == 2,
        )
        keyword_settings = (await session.execute(stmt)).scalars().all()
        for keyword_setting in keyword_settings:
            keyword_setting.hard_status = 1
        await session.commit()
    async with sm() as session:
        stmt_adv_setting = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
        adv = cast(AdvSetting, (await session.execute(stmt_adv_setting)).scalar_one_or_none())
    assert adv
    data = await state.get_data()
    wb_user_cabinet_id: int = data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        stmt_wb_user_cabinet = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_id)
        wb_user_cabinet = cast(WBUserCabinet, (await session.execute(stmt_wb_user_cabinet)).scalar_one_or_none())
    assert wb_user_cabinet
    if callback.from_user is None:
        return
    await bot.send_message(user_telegram_id, "Белый список сброшен, возвращаю меню кампании...")
    await messages.AdvSettingMenu(bot, user_telegram_id, wb_user_cabinet, adv)()  # type: ignore
