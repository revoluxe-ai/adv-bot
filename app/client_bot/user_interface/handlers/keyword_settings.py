"""Обработчики настройки ключевых слов с явными PG session seams."""

# TODO:  Тут большое число mypy ошибок


# type: ignore
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, cast

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.client_bot import const, utils
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers.start_registration_func import (
    start_registration,
)
from app.client_bot.user_interface.views.messages.adv_keyword_messages.keywords_daily_stats_message import (
    KeywordsDailyStatsScreen,
)
from app.client_bot.user_interface.views.messages.adv_keyword_messages.keyword_daily_history_message import (
    KeywordDailyHistoryScreen,
)

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBUserCabinet,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    is_ab_hold_structural_freeze,
)
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    sync_keyword_setting_mode_for_v3,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_adv_updater import data_manager
from app.utils import redis_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from app.client_bot.user_interface.utils import (
    format_target_place_display,
    get_auto_target_place_manual_change_locked_text,
    get_effective_keyword_target_place,
)
from ..helpers.wb_user_cabinet import get_wb_user_cabinet_id_or_none
from ..views import callbacks, messages

logger = logging.getLogger(__name__)


router = Router()


_sm = get_async_session_maker


@dataclass(frozen=True)
class KeywordHardStatusChangeOutcome:
    """Результат ``change_keyword_hard_status_in_session``.

    Attributes:
        kind: ``blocked`` (A/B Hold freeze), ``applied`` (hard_status≥0
            закоммичен), ``needs_ctr_boost`` (``new_hard_status < 0`` —
            caller продолжает CH/CTR и commit).
        keyword_setting: загруженный KeywordSetting (если найден).
        adv_setting: связанный AdvSetting (если найден).
    """

    kind: Literal["blocked", "applied", "needs_ctr_boost"]
    keyword_setting: KeywordSetting | None = None
    adv_setting: AdvSetting | None = None


async def change_keyword_hard_status_in_session(
    session: AsyncSession,
    *,
    keyword_setting_original_id: int,
    new_hard_status: int,
) -> KeywordHardStatusChangeOutcome:
    """Freeze-gate + hard_status mutation в injectable WRITE session.

    Parent ``change_keyword_hard_status`` открывает ``_sm(read_only=False)``
    и передаёт session сюда. Под structural freeze mutation/commit Forbidden.

    Для ``new_hard_status >= 0``: sync mode, commit, ``kind=applied``.
    Для CTR-boost path (``new_hard_status < 0``): возвращает loaded entities
    без commit — caller завершает CH-статистику и commit.

    Args:
        session: injectable async session (WRITE).
        keyword_setting_original_id: PK ``KeywordSetting.id``.
        new_hard_status: целевой hard_status (или отрицательный CTR-boost).

    Returns:
        ``KeywordHardStatusChangeOutcome`` с kind и опциональными entities.
    """
    result = await session.execute(
        select(KeywordSetting)
        .options(selectinload(KeywordSetting.adv_setting))
        .where(KeywordSetting.id == keyword_setting_original_id)
    )
    keyword_setting: KeywordSetting | None = result.scalar()  # noqa
    assert keyword_setting
    adv_setting: AdvSetting = keyword_setting.adv_setting  # type: ignore[attr-defined]
    if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
        return KeywordHardStatusChangeOutcome(
            kind="blocked",
            keyword_setting=keyword_setting,
            adv_setting=adv_setting,
        )
    if new_hard_status < 0:
        return KeywordHardStatusChangeOutcome(
            kind="needs_ctr_boost",
            keyword_setting=keyword_setting,
            adv_setting=adv_setting,
        )
    keyword_setting.hard_status = new_hard_status  # type: ignore[attr-defined]
    _ = sync_keyword_setting_mode_for_v3(
        keyword_setting,
        automatic_version=adv_setting.automatic_version,
        hard_status_override=new_hard_status,
        adv_strategy=adv_setting.strategy,
    )
    if new_hard_status == 2 or new_hard_status == const.ALWAYS_ON:
        keyword_setting.relevant = True  # type: ignore[attr-defined]
    elif new_hard_status == 0:
        keyword_setting.relevant = False  # type: ignore[attr-defined]
    await session.commit()
    return KeywordHardStatusChangeOutcome(
        kind="applied",
        keyword_setting=keyword_setting,
        adv_setting=adv_setting,
    )


async def apply_keyword_ctr_boost_with_client(
    client: Any,
    *,
    keyword_setting: KeywordSetting,
    keyword_text: str,
    adv_ids: set[int],
    min_ctr: float,
    boost_percent: int = 10,
) -> int:
    """CH read + mutate ``added_clicks`` для CTR-boost path (hard_status=-1).

    Parent ``change_keyword_hard_status`` открывает ``get_clickhouse_client()``
    и передаёт client сюда. Не коммитит PG — caller делает ``session.commit``.

    Args:
        client: injectable ClickHouse client (prod or test fixture).
        keyword_setting: ORM entity; ``added_clicks`` / ``added_views`` мутируются.
        keyword_text: текст ключа для CH ``norm_query``.
        adv_ids: множество ``adv_id`` для фильтра CH.
        min_ctr: целевой минимальный CTR кампании.
        boost_percent: процент надбавки к min_ctr (default 10).

    Returns:
        Число добавленных кликов (минимум 1 при необходимости boost).
    """
    clicks, views, _ = await data_manager.get_keyword_statistic_clickhouse(
        client,
        keyword_text,
        adv_ids,
    )
    if keyword_setting.added_clicks:
        clicks += keyword_setting.added_clicks
    if keyword_setting.added_views:  # type: ignore[attr-defined]
        views += cast(int, keyword_setting.added_views)

    new_ctr = min_ctr * (1 + boost_percent / 100)
    add_clicks = max([int(round(new_ctr * views - clicks)), 1])

    if not keyword_setting.added_clicks:  # type: ignore[attr-defined]
        keyword_setting.added_clicks = 0  # type: ignore[attr-defined]
    keyword_setting.added_clicks += add_clicks  # type: ignore[attr-defined]
    return int(add_clicks)


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


async def _notify_adv_setting_not_found(bot: aiogram.Bot, chat_id: int) -> None:
    """Сообщить пользователю, что РК по id не найдена."""
    _ = await bot.send_message(chat_id, "Не удалось найти рекламную кампанию.")


async def _load_adv_setting(
    session: AsyncSession,
    adv_original_id: int,
) -> AdvSetting | None:
    """Загрузить рекламную кампанию в переданной read-only PG-сессии.

    Returns:
        AdvSetting или ``None``, если строки с ``adv_original_id`` нет.
    """
    stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_adv_setting_with_cabinet_in_session(
    session: AsyncSession,
    adv_original_id: int,
) -> AdvSetting | None:
    """Загрузить РК с кабинетом в переданной read-only PG-сессии.

    Returns:
        AdvSetting с ``wb_cabinet`` или ``None``, если РК нет.
    """
    stmt = (
        select(AdvSetting)
        .options(selectinload(AdvSetting.wb_cabinet))
        .where(AdvSetting.id == adv_original_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_wb_user_cabinet_for_keyword_screen_in_session(
    session: AsyncSession,
    telegram_user_id: int,
    wb_cabinet_id: int,
) -> WBUserCabinet | None:
    """Найти пользовательский кабинет для экрана ключевых слов."""
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
                User.user_telegram_id == telegram_user_id,
                WBCabinet.id == wb_cabinet_id,
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_user_in_session(
    session: AsyncSession,
    telegram_user_id: int,
) -> User | None:
    """Загрузить пользователя для admin fallback в переданной PG-сессии."""
    result = await session.execute(
        select(User).where(User.user_telegram_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "active_keywords"))
async def setting_keywords_active_keywords(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_original_id
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.status == "good"]
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            await bot.send_message(
                chat_id, "Не удалось найти кабинет пользователя для этой РК."
            )
            return
    main_photos = await data_manager.get_main_photos(nmids[:1])

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
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
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
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            await bot.send_message(
                chat_id, "Не удалось найти кабинет пользователя для этой РК."
            )
            return
    main_photos = await data_manager.get_main_photos(nmids[:1])
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
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.hard_status == 3]
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            await bot.send_message(
                chat_id, "Не удалось найти кабинет пользователя для этой РК."
            )
            return
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)  # type: ignore[attr-defined]
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
async def setting_keywords_phrases_for_white_list(
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
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [
        keyword
        for keyword in keywords
        if keyword.hard_status == 1
        and keyword.status == KeywordStatus.BAD
        and keyword.reason != "max_position"
    ]
    keywords.sort(key=lambda x: x.rating or 0, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            await bot.send_message(
                chat_id, "Не удалось найти кабинет пользователя для этой РК."
            )
            return

    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)  # type: ignore[attr-defined]
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


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "white_list")) # noqa
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
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.hard_status == 2]
    keywords.sort(key=lambda x: x.rating or 0, reverse=True)
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            await bot.send_message(
                chat_id, "Не удалось найти кабинет пользователя для этой РК."
            )
            return

    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)  # type: ignore[attr-defined]
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
async def handle_filter_keywords_by_adv_message(
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
    if message.from_user is None:
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

    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        await _notify_adv_setting_not_found(bot, message.chat.id)
        return
    adv_choice_last_page = state_data.get("adv_choice_last_page", 1)
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    state_data = await state.get_data()
    state_data.update(adv_choice_last_page=1)
    async with _sm(read_only=True) as session:
        wb_user_cabinet = await _load_wb_user_cabinet_for_keyword_screen_in_session(
            session, message.from_user.id, adv_setting.wb_cabinet_id
        )
    if wb_user_cabinet is None:
        raise RuntimeError("Не удалось найти кабинет пользователя для этой РК.")
    wb_user_cabinet_original_id = wb_user_cabinet.id
    nmids = adv_setting.nmids
    main_photos = await data_manager.get_main_photos(nmids[:1])
    await redis_manager.set_check_last_24_hours(adv_original_id)
    chat_id = message.chat.id
    await redis_manager.set_check_last_24_hours(adv_original_id)
    logger.debug("Обработка собщения")
    # Не сбрасываем FSM state намеренно: пользователь остаётся в waiting_for_filter_keywords
    # и может сразу ввести новый набор ключевых слов для фильтрации без повторного входа в сценарий.
    # Сброс state (как в setting_keywords_filter_by_query, ~стр. 783) здесь не нужен — там
    # одноразовый ввод числа, здесь — многократное уточнение фильтра по ключевым словам.
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


@router.callback_query(callbacks.KeywordsDailyStats.filter())
async def keywords_daily_stats(
    callback: CallbackQuery,
    callback_data: callbacks.KeywordsDailyStats,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Открывает отдельный экран с дневной статистикой по ключам."""
    assert callback.message

    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, callback_data.adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return

    async with ChatActionSender.typing(
        bot=bot, chat_id=cast(types.Message, callback.message).chat.id
    ):
        await KeywordsDailyStatsScreen(
            bot=bot,
            chat_id=callback.message.chat.id,
            adv_setting=adv_setting,
            page=callback_data.page,
            keywords_page=callback_data.keywords_page,
            sort_mode=callback_data.sort_mode,
        )()
    return


@router.callback_query(
    callbacks.SettingKeywords.filter( F.type == "hide_keywords_is_not_relevant") # noqa
)
async def setting_keywords_hide_not_relevant(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):
    await state.update_data(hide_keywords_is_not_relevant=True)
    adv_original_id = callback_data.adv_original_id
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1
    if wb_user_cabinet_original_id is None:
        wb_user_cabinet_original_id = await get_wb_user_cabinet_id_or_none(
            callback.from_user.id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet_original_id is None:
            await bot.send_message(
                chat_id, "Не удалось найти кабинет пользователя для этой РК."
            )
            return
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)  # type: ignore[attr-defined]
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
    callbacks.SettingKeywords.filter(F.type == "show_keywords_is_not_relevant") # noqa
)
async def setting_keywords_show_not_relevant(
    callback: CallbackQuery,
    callback_data: callbacks.SettingKeywords,
    bot: aiogram.Bot,
    state: FSMContext,
):
    await state.update_data(hide_keywords_is_not_relevant=False)
    adv_original_id = callback_data.adv_original_id
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id_raw = state_data.get("last_wb_user_cabinet_original_id")
    if not isinstance(wb_user_cabinet_original_id_raw, int):
        raise RuntimeError("Не удалось восстановить кабинет пользователя из состояния.")
    wb_user_cabinet_original_id = wb_user_cabinet_original_id_raw
    nmids = adv_setting.nmids
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1
    main_photos = await data_manager.get_main_photos(nmids[:1])
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


@router.callback_query(callbacks.SettingKeywords.filter(F.type == "by_adv")) # noqa
async def setting_keywords_by_adv(
    callback: CallbackQuery,
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

    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting_with_cabinet_in_session(
            session, adv_original_id
        )
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return

    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    page = callback_data.page
    await state.update_data(last_keyword_setting_page=page)
    state_data = await state.get_data()
    adv_choice_last_page = state_data.get("adv_choice_last_page", 1)
    user_id = callback.from_user.id
    async with _sm(read_only=False) as session:
        wb_user_cabinet = await _load_wb_user_cabinet_for_keyword_screen_in_session(
            session, user_id, adv_setting.wb_cabinet_id
        )
        if wb_user_cabinet is None and user_id in const.ADMINS:
            admin_user = await _load_user_in_session(session, user_id)
            wb_user_cabinet = WBUserCabinet()
            wb_user_cabinet.user = admin_user
            wb_user_cabinet.wb_cabinet = adv_setting.wb_cabinet
            wb_user_cabinet.name = "Автодобавлен"
            session.add(wb_user_cabinet)
            await session.commit()
    if wb_user_cabinet is None:
        raise RuntimeError("Не удалось найти кабинет пользователя для этой РК.")
    wb_user_cabinet_original_id = wb_user_cabinet.id
    nmids = adv_setting.nmids
    if nmids:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    else:
        await messages.NoMainPhotos(bot, callback.message.chat.id)(adv_setting)  # type: ignore[attr-defined]
        return

    chat_id = cast(types.Message, callback.message).chat.id
    await redis_manager.set_check_last_24_hours(adv_original_id)
    logger.debug("Обработка собщения")
    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id, # noqa
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

    chat_id = cast(types.Message, callback.message).chat.id
    await messages.KeywordSettingMessage(
        bot, chat_id, keyword_setting_original_id, page,
        telegram_user_id=callback.from_user.id,
    )()
    return


@router.callback_query(callbacks.KeywordDailyHistory.filter())
async def keyword_daily_history(
    callback: CallbackQuery,
    callback_data: callbacks.KeywordDailyHistory,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Открывает дневную историю по одному ключевому запросу."""
    assert callback.message

    async with ChatActionSender.typing(
        bot=bot, chat_id=cast(types.Message, callback.message).chat.id
    ):
        await KeywordDailyHistoryScreen(
            bot=bot,
            chat_id=callback.message.chat.id,
            keyword_setting_original_id=callback_data.keyword_setting_original_id,
            page=callback_data.page,
        )()
    return


@router.callback_query(callbacks.ChangeKeywordHardStatus.filter())
async def change_keyword_hard_status(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeKeywordHardStatus,
    bot: aiogram.Bot,
    state: FSMContext,
):
    """Меняет hard_status ключа; под A/B Hold structural freeze — отказ.

    При ``PENDING_SETUP`` / ``ACTIVE`` (``is_ab_hold_structural_freeze``)
    hard_status / ``sync_keyword_setting_mode_for_v3`` / commit не выполняются
    (peer: ``keyword_target_place_value``).

    Parent WRITE seam: ``_sm(read_only=False)`` →
    ``change_keyword_hard_status_in_session``; legacy CTR-boost path отложен,
    реальные UI hard_status остаются в диапазоне 0–4. Helper
    ``apply_keyword_ctr_boost_with_client`` сохранён для возможного возврата
    механики.
    """
    # TODO Показать ключи в в не индекса - не работает
    # TODO: Не работает кнопка Скрыть не релевантные фразы
    # TODO: Тестировать дальше - не работает!!!!
    # TODO: Подумать над ограничением фраз
    async with ChatActionSender.typing(
        bot=bot, chat_id=cast(types.Message, callback.message).chat.id
    ):
        new_hard_status = callback_data.new_hard_status
        keyword_setting_original_id = callback_data.keyword_setting_original_id
        async with _sm(read_only=False) as session:
            outcome = await change_keyword_hard_status_in_session(
                session,
                keyword_setting_original_id=keyword_setting_original_id,
                new_hard_status=new_hard_status,
            )
            if outcome.kind == "blocked":
                await bot.send_message(
                    cast(types.Message, callback.message).chat.id,
                    "Кампания в режиме A/B Hold — статус ключа "
                    "заморожен. Чтобы изменить статус, выключите A/B Hold "
                    "на экране режима.",
                )
                return
            if outcome.kind == "needs_ctr_boost":
                keyword_setting = outcome.keyword_setting
                adv_setting = outcome.adv_setting
                assert keyword_setting is not None
                assert adv_setting is not None
                adv_ids: set[int] = set()
                adv_ids.add(adv_setting.adv_id)
                if search_adv_id := adv_setting.search_adv_id:
                    adv_ids.add(search_adv_id)
                # Отложенная старая CTR-boost механика; реальные UI hard_status
                # остаются в диапазоне 0–4.
                # elif new_hard_status == -1:
                #     min_ctr = await data_manager.get_min_ctr(adv_setting)
                #     async with get_clickhouse_client() as client:
                #         await apply_keyword_ctr_boost_with_client(
                #             client,
                #             keyword_setting=keyword_setting,
                #             keyword_text=keyword_setting.text,  # type: ignore[attr-defined]
                #             adv_ids=adv_ids,
                #             min_ctr=min_ctr,
                #         )
                #
                #     await redis_manager.set_auto_block_status(
                #         keyword_setting_original_id, False
                #     )

                await session.commit()
        data = await state.get_data()
        page = data.get("last_keyword_setting_page", 1)

        chat_id = cast(types.Message, callback.message).chat.id
        await messages.KeywordSettingMessage(
            bot, chat_id, keyword_setting_original_id, page,
            telegram_user_id=callback.from_user.id,
        )()

        return



@router.message(StateFilter(states.AdvSetting.waiting_for_filter_by_query))
async def handle_filter_by_query_message(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
):
    text = message.text or ""
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
    if message.from_user is None:
        return
    callback_data = await state.get_data()
    adv_original_id = int(cast(int, callback_data.get("last_adv_original_id")))
    await messages.LongTimeOperation(bot, message.chat.id)()
    async with _sm(read_only=False) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
        if adv_setting is None:
            await _notify_adv_setting_not_found(bot, message.chat.id)
            return
        adv_setting.hide_small_query_keywords = count_query
        await session.commit()
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    page = 1
    await state.update_data(last_keyword_setting_page=page)
    state_data = await state.get_data()
    adv_choice_last_page = state_data.get("adv_choice_last_page", 1)
    async with _sm(read_only=True) as session:
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
        exec_result = await session.execute(stmt)
        wb_user_cabinet = exec_result.scalar_one_or_none()
    if wb_user_cabinet is None:
        raise RuntimeError("Не удалось найти кабинет пользователя для этой РК.")
    wb_user_cabinet_original_id = wb_user_cabinet.id
    nmids = adv_setting.nmids
    main_photos = await data_manager.get_main_photos(nmids[:1])
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
    await bot.send_message(
        cast(types.Message, callback.message).chat.id,
        "Добавленные клики сброшены",
    )
    return


async def change_keyword_target_place_in_session(
    session: AsyncSession,
    callback_query: CallbackQuery,
    callback_data: callbacks.ChangeKeywordTargetPlace,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Открыть ручное изменение target_place в переданной read-only session.

    Parent ``change_keyword_target_place`` открывает ``_sm(read_only=True)`` и
    передаёт session сюда. Здесь загружается KeywordSetting с AdvSetting,
    проверяется lock A/B Hold и готовится экран ввода новой позиции.
    """
    keyword_setting_original_id = callback_data.keyword_setting_original_id
    stmt = (
        select(KeywordSetting)
        .options(selectinload(KeywordSetting.adv_setting))
        .where(KeywordSetting.id == keyword_setting_original_id)
    )
    result = await session.execute(stmt)
    keyword_setting: KeywordSetting | None = result.scalar_one_or_none()
    if keyword_setting is None:
        if callback_query.message:
            _ = await bot.send_message(
                callback_query.message.chat.id,
                "Не удалось найти настройки ключевого слова.",
            )
        return
    if keyword_setting.adv_setting and keyword_setting.adv_setting.auto_update_target_place:
        await state.set_state(state=None)
        if callback_query.message:
            _ = await bot.send_message(
                callback_query.message.chat.id,
                get_auto_target_place_manual_change_locked_text(),
            )
        return

    value, source = get_effective_keyword_target_place(
        keyword_setting,
        keyword_setting.adv_setting,
    )
    current_value_display, _ = format_target_place_display(value, source)

    adv_default_value = (
        keyword_setting.adv_setting.max_place
        if keyword_setting.adv_setting
        else None
    )
    adv_default_display = (
        str(adv_default_value)
        if isinstance(adv_default_value, int) and adv_default_value > 0
        else "Не задана"
    )

    _ = await state.update_data(
        keyword_setting_for_target_place=keyword_setting_original_id
    )
    await state.set_state(states.KeywordTargetPlace.waiting_for_new_target_place)
    if not callback_query.message:
        return

    _ = await messages.KeywordTargetPlacePrompt(
        bot,
        callback_query.message.chat.id,
        current_value_display,
        adv_default_display,
    )()


@router.callback_query(callbacks.ChangeKeywordTargetPlace.filter())
async def change_keyword_target_place(
    callback_query: CallbackQuery,
    callback_data: callbacks.ChangeKeywordTargetPlace,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Открыть ручное изменение target_place через injectable read-only session."""
    async with _sm(read_only=True) as session:
        await change_keyword_target_place_in_session(
            session,
            callback_query,
            callback_data,
            bot,
            state,
        )


async def keyword_target_place_value_in_session(
    session: AsyncSession,
    message: types.Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Сохраняет целевую позицию ключа; missing AdvSetting / A/B Hold — отказ.

    При ``KeywordSetting.adv_setting is None`` — ``Кампания не найдена.`` без
    записи ``target_place`` / commit (FINDING-PBH-016; peer: add_white_phrases
    missing-campaign stop). При ``is_ab_hold_structural_freeze`` — Hold freeze
    без записи. Parent WRITE seam: ``_sm(read_only=False)``.
    """
    data = await state.get_data()
    keyword_setting_original_id = data.get("keyword_setting_for_target_place")
    if not keyword_setting_original_id:
        _ = await bot.send_message(
            message.chat.id,
            "Не удалось определить ключ. Повторите выбор ключевого слова.",
        )
        await state.set_state()
        return
    keyword_setting_original_id = cast(int, keyword_setting_original_id)

    text = message.text or ""
    try:
        target_place = int(text.strip())
    except ValueError:
        _ = await bot.send_message(
            message.chat.id,
            "Введите целое число (0 — использовать позицию кампании).",
        )
        return
    if target_place < 0:
        _ = await bot.send_message(message.chat.id, "Значение не может быть отрицательным.")
        return

    stmt = (
        select(KeywordSetting)
        .options(selectinload(KeywordSetting.adv_setting))
        .where(KeywordSetting.id == keyword_setting_original_id)
    )
    result = await session.execute(stmt)
    keyword_setting: KeywordSetting | None = result.scalar_one_or_none()
    if keyword_setting is None:
        _ = await bot.send_message(
            message.chat.id,
            "Не удалось найти ключ. Повторите выбор ключевого слова.",
        )
        await state.set_state()
        return

    adv_setting = keyword_setting.adv_setting
    if adv_setting is None:  # pyright: ignore[reportUnnecessaryComparison]
        _ = await bot.send_message(message.chat.id, "Кампания не найдена.")
        _ = await state.update_data(keyword_setting_for_target_place=None)
        _ = await state.set_state()
        return
    if adv_setting.auto_update_target_place:
        _ = await state.update_data(keyword_setting_for_target_place=None)
        await state.set_state(state=None)
        _ = await bot.send_message(
            message.chat.id,
            get_auto_target_place_manual_change_locked_text(),
        )
        return
    if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
        _ = await bot.send_message(
            message.chat.id,
            "Кампания в режиме A/B Hold — целевая позиция ключа "
            "заморожена. Чтобы изменить позиции, выключите A/B Hold "
            "на экране режима.",
        )
        _ = await state.update_data(keyword_setting_for_target_place=None)
        await state.set_state()
        return
    keyword_setting.target_place = target_place
    await session.commit()

    display_value = (
        str(target_place)
        if target_place > 0
        else "0 (мин. ставка WB)"
    )
    _ = await messages.KeywordTargetPlaceUpdated(bot, message.chat.id, display_value)()

    if message.from_user is None:
        return
    page = data.get("last_keyword_setting_page", 1)
    await messages.KeywordSettingMessage(
        bot,
        message.chat.id,
        keyword_setting_original_id,
        page,
        telegram_user_id=message.from_user.id,
    )()

    _ = await state.update_data(keyword_setting_for_target_place=None)
    await state.set_state()


@router.message(StateFilter(states.KeywordTargetPlace.waiting_for_new_target_place))
async def keyword_target_place_value(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Сохранить target_place через injectable write session."""
    async with _sm(read_only=False) as session:
        await keyword_target_place_value_in_session(session, message, bot, state)


@router.callback_query(callbacks.SettingKeywords.filter(F == "only_out_index")) # noqa
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
    async with _sm(read_only=True) as session:
        adv_setting = await _load_adv_setting(session, adv_original_id)
    if adv_setting is None:
        chat_id = cast(types.Message, callback.message).chat.id
        await _notify_adv_setting_not_found(bot, chat_id)
        return
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    keywords = [keyword for keyword in keywords if keyword.position == 0]
    keywords.sort(
        key=lambda x: x.predict_ctr if x.predict_ctr is not None else 0.0,
        reverse=True,
    )
    keyword_texts = [keyword.text for keyword in keywords]
    await state.update_data(keywords_filter=keyword_texts)
    await state.update_data(adv_choice_last_page=page)
    state_data = await state.get_data()
    wb_user_cabinet_original_id_raw = state_data.get("last_wb_user_cabinet_original_id")
    if not isinstance(wb_user_cabinet_original_id_raw, int):
        raise RuntimeError("Не удалось восстановить кабинет пользователя из состояния.")
    wb_user_cabinet_original_id = wb_user_cabinet_original_id_raw
    nmids = adv_setting.nmids
    chat_id = cast(types.Message, callback.message).chat.id
    adv_choice_last_page = 1

    main_photos = await data_manager.get_main_photos(nmids[:1])  # type: ignore[attr-defined]

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
