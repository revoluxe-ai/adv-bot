"""Telegram-хендлеры ручного добавления white/fixed/relevant фраз.

Ordinary ``data_manager.add_*_phrases`` — Allowed OFF only. При
``PENDING_SETUP`` / ``ACTIVE`` (``is_ab_hold_structural_freeze``) membership
mutation блокируется до вызова data_manager (peer: keyword_settings /
set_common_bid_manual). Missing AdvSetting (``load_adv_card_ab_hold_mode_in_session``
→ ``None``) — stop с ``Кампания не найдена.`` без membership write (peer:
``add_black_phrases`` / FINDING-PBH-015). Owned keyword-set change path —
WARM_UP ``keyword_edit_open`` only.

``reset_white_list`` / ``reset_non_relevant_phrases`` — ordinary hard_status
writers той же freeze-gate class (FINDING-PBH-010-R1): под structural freeze
hard_status / ``sync_keyword_setting_mode_for_v3`` / commit Forbidden.

PG seams: parent открывает ``sm(read_only=…)`` и передаёт session в
``*_in_session`` children (PURE_READ для freeze-check; WRITE для reset).
"""

from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import AdvSettingMenu
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBUserCabinet,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    is_ab_hold_structural_freeze,
)
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_campaign,
    sync_keyword_setting_mode_for_v3,
)
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()

AB_HOLD_ADD_PHRASES_BLOCKED_MSG = (
    "Кампания в режиме A/B Hold — добавление фраз запрещено. "
    "Чтобы изменить состав фраз, выключите A/B Hold на экране режима."
)

AB_HOLD_HARD_STATUS_RESET_BLOCKED_MSG = (
    "Кампания в режиме A/B Hold — статус ключей заморожен. "
    "Чтобы сбросить список, выключите A/B Hold на экране режима."
)


@dataclass(frozen=True)
class HardStatusResetOutcome:
    """Результат ordinary hard_status reset в injectable WRITE session.

    Attributes:
        blocked: True если A/B Hold structural freeze — mutation запрещён.
        mutated: True если hard_status реально изменён и закоммичен.
    """

    blocked: bool
    mutated: bool


async def load_adv_card_ab_hold_mode_in_session(
    session: AsyncSession,
    adv_setting_id: int,
) -> str | None:
    """PURE_READ: ``card_ab_hold_mode`` кампании для freeze-gate add_* handlers.

    Args:
        session: injectable async session (caller: ``sm(read_only=True)``).
        adv_setting_id: PK ``AdvSetting.id``.

    Returns:
        Режим Hold или ``None``, если AdvSetting не найден.
    """
    adv = await session.get(AdvSetting, adv_setting_id)
    if adv is None:
        return None
    return getattr(adv, "card_ab_hold_mode", None)


async def reset_white_list_in_session(
    session: AsyncSession,
    *,
    adv_setting_id: int,
) -> HardStatusResetOutcome:
    """Сброс WHITE_LIST→AUTO в переданной WRITE session (freeze-gate).

    Args:
        session: injectable async session (``sm(read_only=False)``).
        adv_setting_id: PK ``AdvSetting.id``.

    Returns:
        ``HardStatusResetOutcome``: blocked под Hold, иначе mutated после commit.
    """
    adv = await session.get(AdvSetting, adv_setting_id)
    assert adv is not None
    if is_ab_hold_structural_freeze(adv.card_ab_hold_mode):
        return HardStatusResetOutcome(blocked=True, mutated=False)
    stmt = select(KeywordSetting).where(
        KeywordSetting.adv_setting_id == adv_setting_id,
        KeywordSetting.hard_status == 2,
    )
    keyword_settings = (await session.execute(stmt)).scalars().all()
    for keyword_setting in keyword_settings:
        keyword_setting.hard_status = 1  # type: ignore
        _ = sync_keyword_setting_mode_for_v3(
            keyword_setting,
            bot_active=adv.bot_active,
            hard_status_override=1,
            adv_strategy=adv.strategy,
        )
    await session.commit()
    return HardStatusResetOutcome(blocked=False, mutated=True)


async def reset_non_relevant_phrases_in_session(
    session: AsyncSession,
    *,
    adv_setting_id: int,
) -> HardStatusResetOutcome:
    """Сброс BLACK_LIST→AUTO в переданной WRITE session (freeze-gate).

    Args:
        session: injectable async session (``sm(read_only=False)``).
        adv_setting_id: PK ``AdvSetting.id``.

    Returns:
        ``HardStatusResetOutcome``: blocked под Hold, иначе mutated после commit.
    """
    adv = await session.get(AdvSetting, adv_setting_id)
    assert adv is not None
    if is_ab_hold_structural_freeze(adv.card_ab_hold_mode):
        return HardStatusResetOutcome(blocked=True, mutated=False)
    stmt = update(KeywordSetting).where(
        KeywordSetting.adv_setting_id == adv_setting_id,
        KeywordSetting.hard_status == 0,
    )
    if is_v3_campaign(adv.bot_active):
        stmt = stmt.values(
            hard_status=1,
            strategy_mode=KeywordStrategyMode.OFF,
        )
    else:
        stmt = stmt.values(hard_status=1)
    await session.execute(stmt)
    await session.commit()
    return HardStatusResetOutcome(blocked=False, mutated=True)


async def load_adv_setting_in_session(
    session: AsyncSession,
    adv_setting_id: int,
) -> AdvSetting | None:
    """PURE_READ: загрузить AdvSetting по id (меню после reset).

    Args:
        session: injectable async session (``sm(read_only=True)``).
        adv_setting_id: PK ``AdvSetting.id``.

    Returns:
        AdvSetting или None.
    """
    stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
    return (await session.execute(stmt)).scalar()


async def load_wb_user_cabinet_in_session(
    session: AsyncSession,
    wb_user_cabinet_id: int,
) -> WBUserCabinet | None:
    """PURE_READ: загрузить WBUserCabinet по id (меню после reset).

    Args:
        session: injectable async session (``sm(read_only=True)``).
        wb_user_cabinet_id: PK ``WBUserCabinet.id``.

    Returns:
        WBUserCabinet или None.
    """
    stmt = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_id)
    return (await session.execute(stmt)).scalar()


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
async def waiting_for_white_phrases(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Добавляет white-фразы; missing campaign / Hold freeze — отказ без write."""
    text = message.text
    if not text:
        return
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        mode = await load_adv_card_ab_hold_mode_in_session(session, adv_setting_id)
    if mode is None:
        await message.answer("Кампания не найдена.")
        return
    if is_ab_hold_structural_freeze(mode):
        await message.answer(AB_HOLD_ADD_PHRASES_BLOCKED_MSG)
        return
    await data_manager.add_white_phrases(keywords, adv_setting_id)
    user = message.from_user
    if user is None:
        return
    await messages.WhitePhrasesAdded(bot, user.id)(adv_setting_id)


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
async def waiting_for_fixed_phrases(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Добавляет fixed-фразы; missing campaign / Hold freeze — отказ без write."""
    text = message.text
    if not text:
        return
    keywords = text.split("\n")
    keywords = [k.strip().lower() for k in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        mode = await load_adv_card_ab_hold_mode_in_session(session, adv_setting_id)
    if mode is None:
        await message.answer("Кампания не найдена.")
        return
    if is_ab_hold_structural_freeze(mode):
        await message.answer(AB_HOLD_ADD_PHRASES_BLOCKED_MSG)
        return
    await data_manager.add_fixed_phrases(keywords, adv_setting_id)
    user = message.from_user
    if user is None:
        return
    await messages.FixedPhrasesAdded(bot, user.id)(adv_setting_id)


@router.callback_query(callbacks.AddRelevantPhrases.filter())
async def add_relevant_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddRelevantPhrases,
    state: FSMContext,
):
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddRelevantPhrases.waiting_for_relevant_phrases)
    await messages.WaitingForRelevantPhrases(bot, callback.from_user.id)()


@router.message(StateFilter(states.AddRelevantPhrases.waiting_for_relevant_phrases))
async def waiting_for_relevant_phrases(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Добавляет relevant-фразы; missing campaign / Hold freeze — отказ без write."""
    text = message.text
    if not text:
        return
    keywords = text.split("\n")
    keywords = [keyword.strip().lower() for keyword in keywords]
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        mode = await load_adv_card_ab_hold_mode_in_session(session, adv_setting_id)
    if mode is None:
        await message.answer("Кампания не найдена.")
        return
    if is_ab_hold_structural_freeze(mode):
        await message.answer(AB_HOLD_ADD_PHRASES_BLOCKED_MSG)
        return
    user = message.from_user
    if user is None:
        return
    await messages.LongTimeOperation(bot, user.id)()
    await data_manager.add_relevant_phrases(keywords, adv_setting_id)
    await messages.RelevantPhrasesAdded(bot, user.id, adv_setting_id)()


@router.callback_query(callbacks.ResetWhiteList.filter())
async def reset_white_list(
    callback: CallbackQuery,
    bot: Bot,  # оставь bot ключевым аргументом
    state: FSMContext,
    callback_data: callbacks.ResetWhiteList,
):
    """Сбрасывает WHITE_LIST→AUTO; под A/B Hold structural freeze — отказ без write."""
    await bot.send_message(callback.from_user.id, "Сброс белого списка...")
    adv_setting_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        outcome = await reset_white_list_in_session(
            session, adv_setting_id=adv_setting_id
        )
    if outcome.blocked:
        await bot.send_message(
            callback.from_user.id,
            AB_HOLD_HARD_STATUS_RESET_BLOCKED_MSG,
        )
        return
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_id)
    assert adv
    data = await state.get_data()
    wb_user_cabinet_id: int = data["last_wb_user_cabinet_original_id"]
    async with sm(read_only=True) as session:
        wb_user_cabinet = await load_wb_user_cabinet_in_session(
            session, wb_user_cabinet_id
        )
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
    """Сбрасывает BLACK_LIST→AUTO; под A/B Hold structural freeze — отказ без write."""
    assert callback.from_user
    await bot.send_message(
        callback.from_user.id, "Сброс нерелевантных фраз (чёрный список)..."
    )
    adv_setting_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        outcome = await reset_non_relevant_phrases_in_session(
            session, adv_setting_id=adv_setting_id
        )
    if outcome.blocked:
        await bot.send_message(
            callback.from_user.id,
            AB_HOLD_HARD_STATUS_RESET_BLOCKED_MSG,
        )
        return
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_id)
    assert adv
    data = await state.get_data()
    wb_user_cabinet_id: int = data["last_wb_user_cabinet_original_id"]
    async with sm(read_only=True) as session:
        wb_user_cabinet = await load_wb_user_cabinet_in_session(
            session, wb_user_cabinet_id
        )
    assert wb_user_cabinet
    await bot.send_message(
        callback.from_user.id,
        "Нерелевантные фразы сброшены, возвращаю меню кампании...",
    )
    await AdvSettingMenu(bot, callback.from_user.id, wb_user_cabinet, adv)()
