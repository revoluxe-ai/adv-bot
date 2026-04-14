from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select, update

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import AdvSettingMenu
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBUserCabinet,
)
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(callbacks.AddWhitePhrases.filter())
async def add_white_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddWhitePhrases,
    state: FSMContext,
):
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddWhitePhrases.waiting_for_white_phrases)
    await messages.WaitingForWhitePhrases(
        bot,
        callback.from_user.id,
    )(adv_setting_id)


@router.message(StateFilter(states.AddWhitePhrases.waiting_for_white_phrases))
async def waiting_for_white_phrases(message, bot: Bot, state: FSMContext):
    text = message.text
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    await data_manager.add_white_phrases(keywords, adv_setting_id)
    await messages.WhitePhrasesAdded(bot, message.from_user.id)(adv_setting_id)


@router.callback_query(callbacks.AddFixedPhrases.filter())
async def add_fixed_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddFixedPhrases,
    state: FSMContext,
):
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddFixedPhrases.waiting_for_fixed_phrases)
    await messages.WaitingForFixedPhrases(bot, callback.from_user.id)(adv_setting_id)


@router.message(StateFilter(states.AddFixedPhrases.waiting_for_fixed_phrases))
async def waiting_for_fixed_phrases(message, bot: Bot, state: FSMContext):
    text = message.text
    keywords = text.split("\n")
    keywords = [k.strip().lower() for k in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    await data_manager.add_fixed_phrases(keywords, adv_setting_id)
    await messages.FixedPhrasesAdded(bot, message.from_user.id)(adv_setting_id)


@router.callback_query(callbacks.AddRelevantPhrases.filter())
async def add_relevant_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddRelevantPhrases,
    state: FSMContext,
):
    await callback.answer("Добавление фраз в релевантный список")
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddRelevantPhrases.waiting_for_relevant_phrases)
    await messages.WaitingForRelevantPhrases(bot, callback.from_user.id)()


@router.message(StateFilter(states.AddRelevantPhrases.waiting_for_relevant_phrases))
async def waiting_for_relevant_phrases(message, bot: Bot, state: FSMContext):
    text = message.text
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    await messages.LongTimeOperation(bot, message.from_user.id)()
    await data_manager.add_relevant_phrases(keywords, adv_setting_id)
    await messages.RelevantPhrasesAdded(bot, message.from_user.id, adv_setting_id)()


@router.callback_query(callbacks.ResetWhiteList.filter())
async def reset_white_list(
    callback: CallbackQuery,
    bot: Bot,  # оставь bot ключевым аргументом
    state: FSMContext,
    callback_data: callbacks.ResetWhiteList,
):
    await bot.send_message(callback.from_user.id, "Сброс белого списка...")
    adv_setting_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id,
            KeywordSetting.hard_status == 2,
        )
        keyword_settings = (await session.execute(stmt)).scalars().all()
        for keyword_setting in keyword_settings:
            keyword_setting.hard_status = 1  # type: ignore
        await session.commit()
    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
        adv = (await session.execute(stmt)).scalar()
    assert adv
    data = await state.get_data()
    wb_user_cabinet_id: int = data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_id)
        wb_user_cabinet = (await session.execute(stmt)).scalar()
    assert wb_user_cabinet
    await bot.send_message(
        callback.from_user.id, "Белый список сброшен, возвращаю меню кампании..."
    )
    await AdvSettingMenu(bot, callback.from_user.id, wb_user_cabinet, adv)()


@router.callback_query(callbacks.ResetNonRelevantPhrases.filter())
async def reset_non_relevant_phrases(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    callback_data: callbacks.ResetNonRelevantPhrases,
) -> None:
    assert callback.from_user
    await bot.send_message(
        callback.from_user.id, "Сброс нерелевантных фраз (чёрный список)..."
    )
    adv_setting_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        stmt = (
            update(KeywordSetting)
            .where(
                KeywordSetting.adv_setting_id == adv_setting_id,
                KeywordSetting.hard_status == 0,
            )
            .values(hard_status=1)
        )
        await session.execute(stmt)
        await session.commit()
    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
        adv = (await session.execute(stmt)).scalar()
    assert adv
    data = await state.get_data()
    wb_user_cabinet_id: int = data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_id)
        wb_user_cabinet = (await session.execute(stmt)).scalar()
    assert wb_user_cabinet
    await bot.send_message(
        callback.from_user.id,
        "Нерелевантные фразы сброшены, возвращаю меню кампании...",
    )
    await AdvSettingMenu(bot, callback.from_user.id, wb_user_cabinet, adv)()
    await callback.answer()
