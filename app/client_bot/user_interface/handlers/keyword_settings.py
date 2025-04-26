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

from app.client_bot import utils, const
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers.start_registration_func import (
    start_registration,
)
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
    KeywordStatus,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser.wb_parser import parser
from app.utils import redis_manager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from ..views import callbacks, messages

logger = logging.getLogger(__name__)


router = Router()


_sm = get_async_session_maker


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "filter_by_query"))
async def setting_keywords_filter_by_query(
    callback: types.CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.AdvSetting.waiting_for_filter_by_query)
    assert callback.message
    await messages.FilterByQuery(bot, callback.message.chat.id)()


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "active_keywords"))
async def setting_keywords_active_keywords(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:

    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.status == "good"]
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

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
async def setting_keywords_sort_by_ctr_desc(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:

    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    keywords: list[CalculatedKeyword] = await utils.get_keywords_for_keyboard(
        adv_setting
    )
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    assert callback.message is not None
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return
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
    )(state, "sort_by_ctr_desc")

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return


@router.callback_query(
    callbacks.SettingKeywords.filter(F.type == "show_keywords_is_hard")
)
async def setting_keywords_show_keywords_is_hard(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:

    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
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
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return
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


@router.callback_query(
    callbacks.SettingKeywords.filter(F.type == "phrase_for_adding_to_white_list")
)
async def setting_keywords_white_list(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):

    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    page = callback_data.page
    if not page:
        page = 1
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [
        keyword
        for keyword in keywords
        if keyword.hard_status == 1
        and keyword.status == KeywordStatus.BAD
        and keyword.reason != "max_position"
    ]
    keywords.sort(key=lambda x: x.rating_by_predict_ctr, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1

    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return
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
async def setting_keywords_white_list(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):

    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    page = callback_data.page
    if not page:
        page = 1
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.hard_status == 2]
    keywords.sort(key=lambda x: x.predict_ctr, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1

    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return
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
async def setting_keywords_by_adv(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
):
    text = message.text
    if not text:
        await bot.send_message(
            message.chat.id,
            "Пожалуйста, введите ключевые слова для фильтрации, каждое слово с новой строки",
        )
        return

    if "/start" in text:
        await state.clear()
        await start_registration(message, bot, state)
        return
    filter_keywords = text.splitlines()
    filter_keywords = [
        keyword.strip().lower() for keyword in filter_keywords if keyword
    ]
    await state.update_data(keywords_filter=filter_keywords)
    await message.answer("Пожалуйста подождите, эта операция займет немного времени")
    await state.set_state(states.AdvSetting.waiting_for_filter_keywords)
    state_data = await state.get_data()
    adv_original_id = state_data.get("last_adv_original_id")
    if not adv_original_id:
        await message.answer(
            f"Не удалось получить идентификатор объявления. Возможно, что нарушен порядок операций"
            f" Попробуйте еще раз, если будут постоянные проблемы, то обратитесь в поддержку {const.SUPPORT_LINK}"
        )
        return

    async with _sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    adv_choice_last_page = state_data.get("adv_choice_last_page", 1)
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    state_data = await state.get_data()
    state_data.update(adv_choice_last_page=1)
    async with _sm() as session:
        stmt = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(
                    WBCabinet.adv_settings
                ),
            )
            .where(
                and_(
                    User.user_telegram_id == message.from_user.id,
                    WBCabinet.id == adv_setting.wb_cabinet_id,
                )
            )
        )
        wb_user_cabinet = await session.execute(stmt)
    wb_user_cabinet = wb_user_cabinet.scalar_one_or_none()
    wb_user_cabinet_original_id = wb_user_cabinet.id
    nmids = adv_setting.nmids
    chat_id = message.chat.id

    if nmids:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    else:
        main_photos = None
    if not main_photos:
        await messages.NoMainPhotos(
            bot,
            chat_id,
        )(adv_setting)
        await redis_manager.set_check_last_24_hours(adv_original_id)
        return

    chat_id = message.chat.id
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


@router.callback_query(
    callbacks.SettingKeywords.filter(F.type == "hide_keywords_is_not_relevant")
)
async def setting_keywords_hide_keywords_is_hard(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):

    await state.update_data(hide_keywords_is_not_relevant=True)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return
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


@router.callback_query(
    callbacks.SettingKeywords.filter(F.type == "show_keywords_is_not_relevant")
)
async def setting_keywords_hide_keywords_is_hard(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):

    await state.update_data(hide_keywords_is_not_relevant=False)
    adv_original_id = callback_data.adv_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return
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


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "by_adv"))
async def setting_keywords_by_adv(
    callback: callbacks.SettingKeywords,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):
    if callback_data.reset_filter:
        await state.update_data(keywords_filter=None)
    await state.set_state(states.AdvSetting.waiting_for_filter_keywords)
    adv_original_id: int = callback_data.adv_original_id
    await state.update_data(
        last_adv_original_id=adv_original_id, last_adv_page=callback_data.page
    )

    async with _sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()

    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    page = callback_data.page
    await state.update_data(last_keyword_setting_page=page)
    state_data = await state.get_data()
    adv_choice_last_page = state_data.get("adv_choice_last_page", 1)
    async with _sm(read_only=False) as session:
        stmt = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(
                    WBCabinet.adv_settings
                ),
            )
            .where(
                and_(
                    User.user_telegram_id == callback.from_user.id,
                    WBCabinet.id == adv_setting.wb_cabinet_id,
                )
            )
        )
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar_one_or_none()
    user_id: int = callback.from_user.id
    if wb_user_cabinet is None and user_id in const.ADMINS:
        stmt = select(User).where(User.user_telegram_id == user_id)
        admin_user = await session.execute(stmt)
        admin_user = admin_user.scalar()
        wb_user_cabinet = WBUserCabinet()
        wb_user_cabinet.user = admin_user
        wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
        wb_user_cabinet.name = "Автодобавлен"
        session.add(wb_user_cabinet)
        await session.commit()
    wb_user_cabinet_original_id = wb_user_cabinet.id
    nmids = adv_setting.nmids
    if nmids:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    else:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return

    chat_id = callback.message.chat.id
    await redis_manager.set_check_last_24_hours(adv_original_id)
    logger.debug("Обработка собщения")
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
async def setting_keyword(
    callback: types.CallbackQuery,
    callback_data: callbacks.SettingKeyword,
    bot: aiogram.Bot,
    state: FSMContext,
):

    keyword_setting_original_id: int = callback_data.keyword_setting_original_id

    data = await state.get_data()
    page = data.get("last_keyword_setting_page", 1)

    chat_id = callback.message.chat.id
    await messages.KeywordSettingMessage(
        bot, chat_id, keyword_setting_original_id, page
    )()
    return


@router.callback_query(callbacks.ChangeKeywordHardStatus.filter())
async def change_keyword_hard_status(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeKeywordHardStatus,
    bot: aiogram.Bot,
    state: FSMContext,
):
    async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
        new_hard_status = callback_data.new_hard_status
        keyword_setting_original_id = callback_data.keyword_setting_original_id
        async with _sm(read_only=False) as session:
            keyword_setting = await session.execute(
                select(KeywordSetting)
                .options(selectinload(KeywordSetting.adv_setting))
                .where(KeywordSetting.id == keyword_setting_original_id)
            )
            keyword_setting: KeywordSetting = keyword_setting.scalar()
            adv_setting = keyword_setting.adv_setting
            if new_hard_status >= 0:
                keyword_setting.hard_status = new_hard_status

            elif new_hard_status == -1:
                min_ctr = await data_manager.get_min_ctr(adv_setting)
                async with get_clickhouse_client() as client:
                    clicks, views, _ = (
                        await data_manager.get_keyword_statistic_clickhouse(
                            client, keyword_setting.text, adv_setting.adv_id
                        )
                    )
                if keyword_setting.added_clicks:
                    clicks += keyword_setting.added_clicks
                if keyword_setting.added_views:
                    views += keyword_setting.added_views

                n = 10  # Процент увеличения CTR, который вы хотите достичь

                # Расчет нового CTR
                new_ctr = min_ctr * (1 + n / 100)

                # Вычисление необходимого количества дополнительных кликов
                add_clicks = max([int(round(new_ctr * views - clicks)), 1])

                # Добавление кликов без изменения показов
                if not keyword_setting.added_clicks:
                    keyword_setting.added_clicks = 0
                keyword_setting.added_clicks += add_clicks

                await redis_manager.set_auto_block_status(
                    keyword_setting_original_id, False
                )

            await session.commit()
        data = await state.get_data()
        page = data.get("last_keyword_setting_page", 1)

        chat_id = callback.message.chat.id
        await messages.KeywordSettingMessage(
            bot, chat_id, keyword_setting_original_id, page
        )()

        return


@router.callback_query(callbacks.CheckPosition.filter())
async def check_position(
    callback: types.CallbackQuery,
    callback_data: callbacks.CheckPosition,
    bot: aiogram.Bot,
):

    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    keyword_setting_original_id = callback_data.keyword_setting_original_id
    async with _sm() as session:
        result = await session.execute(
            select(KeywordSetting.text).where(
                KeywordSetting.id == keyword_setting_original_id
            )
        )
        text: KeywordSetting = result.scalar()
        adv_setting_original_id = callback_data.adv_original_id
        stmt = select(AdvSetting.nmids).where(AdvSetting.id == adv_setting_original_id)
        result = await session.execute(stmt)
        nmids: AdvSetting = result.scalar()
        nmid = nmids[0]
    await parser.add_wb_positions(text, {nmid}, delay=3)
    await messages.KeywordSettingMessage(
        bot, callback.message.chat.id, keyword_setting_original_id, 1
    )()


@router.message(StateFilter(states.AdvSetting.waiting_for_filter_by_query))
async def setting_keywords_filter_by_query(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
):
    text = message.text
    if "/start" in text:
        await state.clear()
        await start_registration(message, bot, state)
        return
    try:
        count_query = int(text)
    except ValueError:
        await message.answer("Введите число от нуля и выше:")
        return
    if count_query < 0:
        count_query *= -1
    callback_data = await state.get_data()
    adv_original_id = int(callback_data.get("last_adv_original_id"))
    await messages.LongTimeOperation(bot, message.chat.id)()
    async with _sm(read_only=False) as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
        adv_setting.hide_small_query_keywords = count_query
        await session.commit()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    page = 1
    await state.update_data(last_keyword_setting_page=page)
    state_data = await state.get_data()
    adv_choice_last_page = state_data.get("adv_choice_last_page", 1)
    async with _sm() as session:
        stmt = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(
                    WBCabinet.adv_settings
                ),
            )
            .where(
                and_(
                    User.user_telegram_id == message.from_user.id,
                    WBCabinet.id == adv_setting.wb_cabinet_id,
                )
            )
        )
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar_one_or_none()
    wb_user_cabinet_original_id = wb_user_cabinet.id
    nmids = adv_setting.nmids
    if nmids:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    else:
        await messages.NoMainPhotos(bot, message.chat.id)(adv_setting)
        return

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
        page,
    )(state)
    logger.debug("Отправили сообщение")
    await redis_manager.set_check_last_24_hours(adv_original_id)


@router.callback_query(callbacks.ResetAddedClicks.filter())
async def reset_added_clicks(
    callback: types.CallbackQuery,
    callback_data: callbacks.ResetAddedClicks,
    bot: aiogram.Bot,
):

    adv_setting_original_id = callback_data.adv_setting_original_id
    async with _sm(read_only=False) as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_original_id
        )
        result = await session.execute(stmt)
        keyword_settings = result.scalars().all()
        for keyword_setting in keyword_settings:
            keyword_setting.added_clicks = 0
        await session.commit()
    await bot.send_message(callback.message.chat.id, "Добавленные клики сброшены")
    return


@router.callback_query(callbacks.SettingKeywords.filter(F == "only_out_index"))
async def show_only_on_out_index(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    page = callback_data.page
    if not page:
        page = 1
    async with _sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.id == adv_original_id,
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.base_position == 0]
    keywords.sort(key=lambda x: x.predict_ctr, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = callback.message.chat.id
    adv_choice_last_page = 1

    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)
        return
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
    )(state, "only_out_index")

    await redis_manager.set_check_last_24_hours(adv_original_id)
    return
