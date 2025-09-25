import logging

import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Any, cast

from app.client_bot import const, utils
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers.start_registration_func import start_registration
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting, WBCabinet, WBUserCabinet
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser.wb_parser import parser
from app.utils import redis_manager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from ..helpers.wb_user_cabinet import get_wb_user_cabinet_id_or_none
from ..views import callbacks, messages

logger = logging.getLogger(__name__)


router = Router()


_sm = get_async_session_maker


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "filter_by_query"))
async def setting_keywords_filter_by_query_callback(
    callback: types.CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.AdvSetting.waiting_for_filter_by_query)
    assert callback.message is not None
    assert callback.message.chat is not None
    await messages.FilterByQuery(bot, callback.message.chat.id)()


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "active_keywords"))
async def setting_keywords_active_keywords_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result_adv_setting = await session.execute(stmt)
        adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.status == "good"]
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int | None = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Не удалось найти кабинет пользователя для этой РК.")
            return
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "sort_by_ctr_desc"))
async def setting_keywords_sort_by_ctr_desc_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result_adv_setting = await session.execute(stmt)
        adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords: list[CalculatedKeyword] = await utils.get_keywords_for_keyboard(adv_setting)
    keywords.sort(key=lambda x: x.predict_ctr if x.predict_ctr is not None else -1.0, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    final_wb_user_cabinet_original_id: int | None = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    if final_wb_user_cabinet_original_id is None:
        if callback.from_user.id in const.ADMINS:
            user_id = callback.from_user.id
            async with _sm(read_only=False) as session_admin:
                stmt_admin_user = select(User).where(User.user_telegram_id == user_id)
                admin_user: User | None = (await session_admin.execute(stmt_admin_user)).scalar_one_or_none()
                if admin_user is None:
                    await bot.send_message(callback.message.chat.id, "Пользователь не найден.")
                    return
                wb_user_cabinet = WBUserCabinet()
                wb_user_cabinet.user = admin_user
                wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
                wb_user_cabinet.name = "Автодобавлен"
                session_admin.add(wb_user_cabinet)
                await session_admin.commit()
                await session_admin.refresh(wb_user_cabinet)
        else:
            await bot.send_message(callback.message.chat.id, "Кабинет пользователя не найден.")
            return
    final_wb_user_cabinet_original_id = wb_user_cabinet.id
    if final_wb_user_cabinet_original_id is None:
        assert callback.message is not None
        await bot.send_message(callback.message.chat.id, "Не удалось получить ID кабинета пользователя.")
        return
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        final_wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=callback_data.page,
    )(state, "sort_by_ctr_desc")

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "show_keywords_is_hard"))
async def setting_keywords_show_keywords_is_hard(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting | None = result.scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.hard_status == 3]
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Не удалось найти кабинет пользователя для этой РК.")
            return
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "phrase_for_adding_to_white_list"))
async def setting_keywords_phrase_for_adding_to_white_list_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    page = callback_data.page
    if not page:
        page = 1
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result_adv_setting = await session.execute(stmt)
        adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [
        keyword
        for keyword in keywords
        if keyword.hard_status == 1 and keyword.status == KeywordStatus.BAD and keyword.reason != "max_position"
    ]
    keywords.sort(key=lambda x: x.rating_by_predict_ctr, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int | None = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Не удалось найти кабинет пользователя для этой РК.")
            return

    assert callback.message is not None
    assert callback.message.chat is not None
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=page,
        image_mode="main_photo",
    )(state)

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "white_list"))
async def setting_keywords_white_list_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    page = callback_data.page
    if not page:
        page = 1
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result_adv_setting = await session.execute(stmt)
        adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.hard_status == 2]
    keywords.sort(key=lambda x: x.predict_ctr if x.predict_ctr is not None else -1.0, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int | None = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Не удалось найти кабинет пользователя для этой РК.")
            return

    assert callback.message is not None
    assert callback.message.chat is not None
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=page,
    )(state, "white_list")

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.message(StateFilter(states.AdvSetting.waiting_for_filter_keywords))
async def setting_keywords_by_adv_message(
    message: types.Message,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if message.text is None:
        return
    if message.from_user is None:
        return
    text = message.text
    if "/start" in text:
        await state.clear()
        await start_registration(message, bot, state)
        return
    filter_keywords = text.splitlines()
    filter_keywords = [keyword.strip().lower() for keyword in filter_keywords if keyword]
    await state.update_data(keywords_filter=filter_keywords)
    await message.answer("Пожалуйста подождите, эта операция займет немного времени")
    await state.set_state(states.AdvSetting.waiting_for_filter_keywords)
    state_data = await state.get_data()
    adv_original_id: int | None = state_data.get("last_adv_original_id")
    if adv_original_id is None:
        assert message.chat is not None
        await message.answer(
            f"Не удалось получить идентификатор объявления. Возможно, что нарушен порядок операций"
            f" Попробуйте еще раз, если будут постоянные проблемы, то обратитесь в поддержку {const.SUPPORT_LINK}"
        )
        return

    async with _sm() as session:
        stmt_adv_setting = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        adv_setting: AdvSetting | None = (await session.execute(stmt_adv_setting)).scalar_one_or_none()
        if adv_setting is None:
            assert message.chat is not None
            await bot.send_message(message.chat.id, "Настройка рекламы не найдена.")
            return
    adv_choice_last_page: int = state_data.get("adv_choice_last_page", 1)
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    state_data = await state.get_data()
    state_data.update(adv_choice_last_page=1)
    async with _sm() as session:
        stmt_wb_user_cabinet = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(WBCabinet.adv_settings),
            )
            .where(
                and_(
                    User.user_telegram_id == message.from_user.id,
                    WBCabinet.id == adv_setting.wb_cabinet_id,
                )
            )
        )
        wb_user_cabinet: WBUserCabinet | None = (await session.execute(stmt_wb_user_cabinet)).scalar_one_or_none()
    if wb_user_cabinet is None:
        if message.from_user.id in const.ADMINS:
            user_id = message.from_user.id
            async with _sm(read_only=False) as session_admin:
                stmt_admin_user = select(User).where(User.user_telegram_id == user_id)
                admin_user: User | None = (await session_admin.execute(stmt_admin_user)).scalar_one_or_none()
                if admin_user is None:
                    assert message.chat is not None
                    await bot.send_message(message.chat.id, "Пользователь не найден.")
                    return
                wb_user_cabinet = WBUserCabinet()
                wb_user_cabinet.user = admin_user
                wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
                wb_user_cabinet.name = "Автодобавлен"
                session_admin.add(wb_user_cabinet)
                await session_admin.commit()
                await session_admin.refresh(wb_user_cabinet)
        else:
            assert message.chat is not None
            await bot.send_message(message.chat.id, "Кабинет пользователя не найден.")
            return
    wb_user_cabinet_original_id: int | None = wb_user_cabinet.id
    if wb_user_cabinet_original_id is None:
        assert message.chat is not None
        await bot.send_message(message.chat.id, "Не удалось получить ID кабинета пользователя.")
        return
    nmids = adv_setting.nmids
    if nmids:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    else:
        main_photos = None
    if not main_photos:
        assert message.chat is not None
        await messages.NoMainPhotos(
            bot,
            message.chat.id,
        )(adv_setting)
        await redis_manager.set_check_last_24_hours(adv_original_id)
        return

    assert message.chat is not None
    chat_id = message.chat.id
    await redis_manager.set_check_last_24_hours(adv_original_id)
    logger.debug("Обработка собщения")
    await state.set_state()
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)

    logger.debug("Отправили сообщение")
    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "hide_keywords_is_not_relevant"))
async def setting_keywords_hide_keywords_is_hard_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(hide_keywords_is_not_relevant=True)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt_adv_setting = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        adv_setting: AdvSetting | None = (await session.execute(stmt_adv_setting)).scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int | None = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Не удалось найти кабинет пользователя для этой РК.")
            return
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "show_keywords_is_not_relevant"))
async def setting_keywords_show_keywords_is_not_relevant_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(hide_keywords_is_not_relevant=False)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt_adv_setting = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        adv_setting: AdvSetting | None = (await session.execute(stmt_adv_setting)).scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    final_wb_user_cabinet_original_id: int | None = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1

    assert callback.message is not None
    assert callback.message.chat is not None
    if final_wb_user_cabinet_original_id is None:
        if callback.from_user.id in const.ADMINS:
            user_id = callback.from_user.id
            async with _sm(read_only=False) as session_admin:
                stmt_admin_user = select(User).where(User.user_telegram_id == user_id)
                admin_user: User | None = (await session_admin.execute(stmt_admin_user)).scalar_one_or_none()
                if admin_user is None:
                    assert callback.message is not None
                    await bot.send_message(callback.message.chat.id, "Пользователь не найден.")
                    return
                wb_user_cabinet = WBUserCabinet()
                wb_user_cabinet.user = admin_user
                wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
                wb_user_cabinet.name = "Автодобавлен"
                session_admin.add(wb_user_cabinet)
                await session_admin.commit()
                await session_admin.refresh(wb_user_cabinet)
        else:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Кабинет пользователя не найден.")
            return
    final_wb_user_cabinet_original_id = wb_user_cabinet.id
    if final_wb_user_cabinet_original_id is None:
        assert callback.message is not None
        await bot.send_message(callback.message.chat.id, "Не удалось получить ID кабинета пользователя.")
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        final_wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=callback_data.page,
    )(state)

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "by_adv"))
async def setting_keywords_by_adv_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    if callback_data.reset_filter:
        await state.update_data(keywords_filter=None)
    await state.set_state(states.AdvSetting.waiting_for_filter_keywords)
    adv_original_id: int = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id, last_adv_page=callback_data.page)

    async with _sm() as session:
        stmt_adv_setting = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        adv_setting: AdvSetting | None = (await session.execute(stmt_adv_setting)).scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return

    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    page = callback_data.page
    await state.update_data(last_keyword_setting_page=page)
    state_data = await state.get_data()
    adv_choice_last_page: int = state_data.get("adv_choice_last_page", 1)
    async with _sm(read_only=False) as session:
        stmt_wb_user_cabinet = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(WBCabinet.adv_settings),
            )
            .where(
                and_(
                    User.user_telegram_id == callback.from_user.id,
                    WBCabinet.id == adv_setting.wb_cabinet_id,
                )
            )
        )
        wb_user_cabinet: WBUserCabinet | None = (await session.execute(stmt_wb_user_cabinet)).scalar_one_or_none()
    if wb_user_cabinet is None:
        if callback.from_user.id in const.ADMINS:
            user_id = callback.from_user.id
            async with _sm(read_only=False) as session_admin:
                stmt_admin_user = select(User).where(User.user_telegram_id == user_id)
                admin_user: User | None = (await session_admin.execute(stmt_admin_user)).scalar_one_or_none()
                if admin_user is None:
                    assert callback.message is not None
                    await bot.send_message(callback.message.chat.id, "Пользователь не найден.")
                    return
                wb_user_cabinet = WBUserCabinet()
                wb_user_cabinet.user = admin_user
                wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
                wb_user_cabinet.name = "Автодобавлен"
                session_admin.add(wb_user_cabinet)
                await session_admin.commit()
                await session_admin.refresh(wb_user_cabinet)
        else:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Кабинет пользователя не найден.")
            return
    wb_user_cabinet_original_id: int | None = wb_user_cabinet.id
    if wb_user_cabinet_original_id is None:
        assert callback.message is not None
        await bot.send_message(callback.message.chat.id, "Не удалось получить ID кабинета пользователя.")
        return
    nmids = adv_setting.nmids
    if nmids:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    else:
        main_photos = None
    if not main_photos:
        assert callback.message is not None
        await messages.NoMainPhotos(
            bot,
            callback.message.chat.id,
        )(adv_setting)
        await redis_manager.set_check_last_24_hours(adv_original_id)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    chat_id = callback.message.chat.id
    await redis_manager.set_check_last_24_hours(adv_original_id)
    logger.debug("Обработка собщения")
    await state.set_state()
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page,
    )(state)
    logger.debug("Отправили сообщение")
    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


# @router.callback_query(callbacks.SettingKeywords.filter())
# async def setting_keywords(callback: types.CallbackQuery, callback_data: callbacks.SettingKeyword, bot: aiogram.Bot,
#                            state: FSMContext):
#
#     keyword_original_id: int = callback_data.keyword_original_id
#     chat_id = callback.message.chat.id
#
#     data = await state.get_data()
#     page = data.get('last_keyword_setting_page', 1)
#     await messages.KeywordSettingMessage(bot, chat_id, keyword_original_id, page)()
#
#     return


@router.callback_query(callbacks.SettingKeyword.filter())
async def setting_keyword_callback(
    callback: types.CallbackQuery,
    callback_data: callbacks.SettingKeyword,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    keyword_setting_original_id: int = callback_data.keyword_setting_original_id

    data = await state.get_data()
    page = data.get("last_keyword_setting_page", 1)

    assert callback.message is not None
    assert callback.message.chat is not None
    chat_id = callback.message.chat.id
    await messages.KeywordSettingMessage(bot, chat_id, keyword_setting_original_id, page)()
    return


@router.callback_query(callbacks.ChangeKeywordHardStatus.filter())
async def change_keyword_hard_status_callback(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeKeywordHardStatus,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
        new_hard_status = callback_data.new_hard_status
        keyword_setting_original_id = callback_data.keyword_setting_original_id
        async with _sm(read_only=False) as session:
            result_keyword_setting = await session.execute(
                select(KeywordSetting)
                .options(selectinload(KeywordSetting.adv_setting))
                .where(KeywordSetting.id == keyword_setting_original_id)
            )
            keyword_setting: KeywordSetting | None = result_keyword_setting.scalar_one_or_none()
            if keyword_setting is None:
                assert callback.message is not None
                await bot.send_message(callback.message.chat.id, "Настройка ключевого слова не найдена.")
                return
            adv_setting: AdvSetting = keyword_setting.adv_setting
            if new_hard_status >= 0:
                keyword_setting.hard_status = new_hard_status
                if new_hard_status == 2:
                    keyword_setting.relevant = True
                elif new_hard_status == 0:
                    keyword_setting.relevant = False
            adv_ids = set()
            adv_ids.add(adv_setting.adv_id)
            if search_adv_id := adv_setting.search_adv_id:
                adv_ids.add(search_adv_id)
            elif new_hard_status == -1:
                min_ctr = await data_manager.get_min_ctr(adv_setting)
                async with get_clickhouse_client() as client:
                    assert keyword_setting.text is not None
                    (
                        clicks,
                        views,
                        _,
                    ) = await data_manager.get_keyword_statistic_clickhouse(client, keyword_setting.text, adv_ids)
                if keyword_setting.added_clicks:
                    clicks += keyword_setting.added_clicks
                if keyword_setting.added_views:
                    views += keyword_setting.added_views

                n = 10  # Процент увеличения CTR, который вы хотите достичь

                # Расчет нового CTR
                min_ctr_value = min_ctr if min_ctr is not None else 0.0
                new_ctr = min_ctr_value * (1 + n / 100)

                # Вычисление необходимого количества дополнительных кликов
                add_clicks = max([int(round(new_ctr * views - clicks)), 1])

                # Добавление кликов без изменения показов
                if keyword_setting.added_clicks is None:
                    keyword_setting.added_clicks = 0
                keyword_setting.added_clicks += add_clicks

                await redis_manager.set_auto_block_status(keyword_setting_original_id, False)

            await session.commit()
        data = await state.get_data()
        page = data.get("last_keyword_setting_page", 1)

        assert callback.message is not None
        assert callback.message.chat is not None
        chat_id = callback.message.chat.id
        await messages.KeywordSettingMessage(bot, chat_id, keyword_setting_original_id, page)()

        return


@router.callback_query(callbacks.CheckPosition.filter())
async def check_position_callback(
    callback: types.CallbackQuery,
    callback_data: callbacks.CheckPosition,
    bot: aiogram.Bot,
) -> None:
    if callback.message is None:
        return
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    keyword_setting_original_id = callback_data.keyword_setting_original_id
    async with _sm() as session:
        result_text = await session.execute(
            select(KeywordSetting.text).where(KeywordSetting.id == keyword_setting_original_id)
        )
        text: str | None = result_text.scalar_one_or_none()
        if text is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Текст ключевого слова не найден.")
            return
        adv_setting_original_id = callback_data.adv_original_id
        stmt_nmids = select(AdvSetting.nmids).where(AdvSetting.id == adv_setting_original_id)
        result_nmids = await session.execute(stmt_nmids)
        nmids_list: list[int] | None = result_nmids.scalar_one_or_none()
        if nmids_list is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "NMIDS не найдены для рекламной кампании.")
            return
        if not nmids_list:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Список NMIDS пуст для рекламной кампании.")
            return
        nmid = nmids_list[0]
    await parser.add_wb_positions(text, {nmid}, delay=1)
    assert callback.message is not None
    assert callback.message.chat is not None
    await messages.KeywordSettingMessage(bot, callback.message.chat.id, keyword_setting_original_id, 1)()


@router.message(StateFilter(states.AdvSetting.waiting_for_filter_by_query))
async def setting_keywords_filter_by_query_message(
    message: types.Message,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if message.text is None:
        return
    if message.from_user is None:
        return
    text = message.text
    if "/start" in text:
        await state.clear()
        await start_registration(message, bot, state)
        return
    try:
        count_query = int(text)
    except ValueError:
        assert message.chat is not None
        await message.answer("Введите число от нуля и выше:")
        return
    if count_query < 0:
        count_query *= -1
    callback_data = await state.get_data()
    adv_original_id: int | None = callback_data.get("last_adv_original_id")
    if adv_original_id is None:
        assert message.chat is not None
        await message.answer(
            f"Не удалось получить идентификатор объявления. Возможно, что нарушен порядок операций"
            f" Попробуйте еще раз, если будут постоянные проблемы, то обратитесь в поддержку {const.SUPPORT_LINK}"
        )
        return
    assert message.chat is not None
    await messages.LongTimeOperation(bot, message.chat.id)()
    async with _sm(read_only=False) as session:
        stmt_adv_setting = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        adv_setting: AdvSetting | None = (await session.execute(stmt_adv_setting)).scalar_one_or_none()
        if adv_setting is None:
            assert message.chat is not None
            await bot.send_message(message.chat.id, "Настройка рекламы не найдена.")
            return
        adv_setting.hide_small_query_keywords = count_query
        await session.commit()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    page = 1
    await state.update_data(last_keyword_setting_page=page)
    state_data = await state.get_data()
    adv_choice_last_page: int = state_data.get("adv_choice_last_page", 1)
    async with _sm() as session:
        stmt_wb_user_cabinet = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(WBCabinet.adv_settings),
            )
            .where(
                and_(
                    User.user_telegram_id == message.from_user.id,
                    WBCabinet.id == adv_setting.wb_cabinet_id,
                )
            )
        )
        wb_user_cabinet: WBUserCabinet | None = (await session.execute(stmt_wb_user_cabinet)).scalar_one_or_none()
    if wb_user_cabinet is None:
        if message.from_user.id in const.ADMINS:
            user_id = message.from_user.id
            async with _sm(read_only=False) as session_admin:
                stmt_admin_user = select(User).where(User.user_telegram_id == user_id)
                admin_user: User | None = (await session_admin.execute(stmt_admin_user)).scalar_one_or_none()
                if admin_user is None:
                    assert message.chat is not None
                    await bot.send_message(message.chat.id, "Пользователь не найден.")
                    return
                wb_user_cabinet = WBUserCabinet()
                wb_user_cabinet.user = admin_user
                wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
                wb_user_cabinet.name = "Автодобавлен"
                session_admin.add(wb_user_cabinet)
                await session_admin.commit()
                await session_admin.refresh(wb_user_cabinet)
        else:
            assert message.chat is not None
            await bot.send_message(message.chat.id, "Кабинет пользователя не найден.")
            return
    wb_user_cabinet_original_id: int | None = wb_user_cabinet.id
    if wb_user_cabinet_original_id is None:
        assert message.chat is not None
        await bot.send_message(message.chat.id, "Не удалось получить ID кабинета пользователя.")
        return
    nmids = adv_setting.nmids
    if nmids:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    else:
        main_photos = None
    if not main_photos:
        assert message.chat is not None
        await messages.NoMainPhotos(
            bot,
            message.chat.id,
        )(adv_setting)
        await redis_manager.set_check_last_24_hours(adv_original_id)
        return

    assert message.chat is not None
    chat_id = message.chat.id
    await redis_manager.set_check_last_24_hours(adv_original_id)
    logger.debug("Обработка собщения")
    await state.set_state()
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)

    logger.debug("Отправили сообщение")
    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(callbacks.ResetAddedClicks.filter())
async def reset_added_clicks(
    callback: types.CallbackQuery,
    callback_data: callbacks.ResetAddedClicks,
    bot: aiogram.Bot,
) -> None:
    if callback.message is None:
        return
    adv_setting_original_id = callback_data.adv_setting_original_id
    async with _sm(read_only=False) as session:
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting_original_id)
        result = await session.execute(stmt)
        keyword_settings = result.scalars().all()
        for keyword_setting in keyword_settings:
            keyword_setting.added_clicks = 0
        await session.commit()
    assert callback.message is not None
    assert callback.message.chat is not None
    await bot.send_message(callback.message.chat.id, "Добавленные клики сброшены")
    return


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "only_out_index"))
async def show_only_on_out_index_callback(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    if callback.from_user is None:
        return
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    page = callback_data.page
    if not page:
        page = 1
    async with _sm() as session:
        stmt_adv_setting = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        adv_setting: AdvSetting | None = (await session.execute(stmt_adv_setting)).scalar_one_or_none()
        if adv_setting is None:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.position == 0]
    keywords.sort(key=lambda x: x.predict_ctr if x.predict_ctr is not None else -1.0, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    final_wb_user_cabinet_original_id: int | None = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1

    assert callback.message is not None
    assert callback.message.chat is not None
    if final_wb_user_cabinet_original_id is None:
        if callback.from_user.id in const.ADMINS:
            user_id = callback.from_user.id
            async with _sm(read_only=False) as session_admin:
                stmt_admin_user = select(User).where(User.user_telegram_id == user_id)
                admin_user: User | None = (await session_admin.execute(stmt_admin_user)).scalar_one_or_none()
                if admin_user is None:
                    assert callback.message is not None
                    await bot.send_message(callback.message.chat.id, "Пользователь не найден.")
                    return
                wb_user_cabinet = WBUserCabinet()
                wb_user_cabinet.user = admin_user
                wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
                wb_user_cabinet.name = "Автодобавлен"
                session_admin.add(wb_user_cabinet)
                await session_admin.commit()
                await session_admin.refresh(wb_user_cabinet)
        else:
            assert callback.message is not None
            await bot.send_message(callback.message.chat.id, "Кабинет пользователя не найден.")
            return
    final_wb_user_cabinet_original_id = wb_user_cabinet.id
    if final_wb_user_cabinet_original_id is None:
        assert callback.message is not None
        await bot.send_message(callback.message.chat.id, "Не удалось получить ID кабинета пользователя.")
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except Exception:
        assert callback.message is not None
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    assert callback.message is not None
    assert callback.message.chat is not None
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        final_wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=page,
    )(state, "only_out_index")

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return
