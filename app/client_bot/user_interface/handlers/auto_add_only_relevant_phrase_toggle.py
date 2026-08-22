"""Telegram-хендлеры меню и toggle ``auto_add_only_relevant_phrase``.

Ordinary WRITE ``AdvSetting.auto_add_only_relevant_phrase`` (membership /
allowed-set policy) — Forbidden under A/B Hold ``PENDING_SETUP`` /
``ACTIVE`` (``is_ab_hold_structural_freeze``). Gate стоит до update/commit
(peer: ``add_black_phrases`` / PBH-012, ``add_relevant_phrase_templates`` /
PBH-013). Keyword-set / membership-policy change — WARM_UP
``keyword_edit_open`` only.

PG seams: parent открывает ``sm(read_only=…)`` и передаёт session в
``load_adv_by_adv_id_in_session`` (PURE_READ) /
``toggle_auto_add_only_relevant_phrase_in_session`` (WRITE + freeze-gate).
"""

from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.client_bot.user_interface.views.callbacks import (
    ChangeAutoAddOnlyRelevantPhraseStatus,
    ManageRelevantAndNonRelevantPhrases,
)
from app.client_bot.user_interface.views.messages.messages import (
    RelevantPhraseManagementMenuMessage,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    is_ab_hold_structural_freeze,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()

AB_HOLD_AUTO_ADD_ONLY_RELEVANT_BLOCKED_MSG = (
    "Кампания в режиме A/B Hold — изменение состава фраз запрещено. "
    "Чтобы изменить политику релевантных фраз, выключите A/B Hold на экране режима."
)


@dataclass(frozen=True)
class AutoAddOnlyRelevantToggleOutcome:
    """Результат toggle ``auto_add_only_relevant_phrase`` в injectable WRITE session.

    Attributes:
        blocked: True если A/B Hold structural freeze — mutation запрещён.
        mutated: True если поле реально обновлено и закоммичено.
        adv: AdvSetting после load (для menu); может быть None если не найден.
    """

    blocked: bool
    mutated: bool
    adv: AdvSetting | None


async def load_adv_by_adv_id_in_session(
    session: AsyncSession,
    adv_id: int,
) -> AdvSetting | None:
    """PURE_READ: загрузить AdvSetting по ``adv_id`` (меню / post-toggle).

    Args:
        session: injectable async session (caller: ``sm(read_only=True)``).
        adv_id: WB advert id ``AdvSetting.adv_id``.

    Returns:
        AdvSetting или ``None``.
    """
    stmt = select(AdvSetting).where(AdvSetting.adv_id == adv_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def load_adv_setting_by_pk_in_session(
    session: AsyncSession,
    adv_setting_id: int,
) -> AdvSetting | None:
    """PURE_READ: загрузить AdvSetting по PK для меню управления релевантностью.

    Args:
        session: injectable async session (caller: ``sm(read_only=True)``).
        adv_setting_id: PK ``AdvSetting.id``.

    Returns:
        AdvSetting или ``None``.
    """
    stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def toggle_auto_add_only_relevant_phrase_in_session(
    session: AsyncSession,
    *,
    adv_id: int,
    new_status: bool,
) -> AutoAddOnlyRelevantToggleOutcome:
    """WRITE: toggle ``auto_add_only_relevant_phrase`` с freeze-gate в session.

    Args:
        session: injectable async session (``sm(read_only=False)``).
        adv_id: WB advert id ``AdvSetting.adv_id``.
        new_status: целевое значение флага.

    Returns:
        ``AutoAddOnlyRelevantToggleOutcome``: blocked под Hold, иначе mutated.
    """
    adv = await load_adv_by_adv_id_in_session(session, adv_id)
    if adv is None:
        return AutoAddOnlyRelevantToggleOutcome(
            blocked=False, mutated=False, adv=None
        )
    if is_ab_hold_structural_freeze(adv.card_ab_hold_mode):
        return AutoAddOnlyRelevantToggleOutcome(
            blocked=True, mutated=False, adv=adv
        )
    stmt = (
        update(AdvSetting)
        .where(AdvSetting.adv_id == adv_id)
        .values({"auto_add_only_relevant_phrase": new_status})
    )
    await session.execute(stmt)
    await session.commit()
    return AutoAddOnlyRelevantToggleOutcome(
        blocked=False, mutated=True, adv=adv
    )


@router.callback_query(ManageRelevantAndNonRelevantPhrases.filter())
async def open_relevant_phrase_management_menu(
    callback_query: CallbackQuery,
    callback_data: ManageRelevantAndNonRelevantPhrases,
    bot: Bot,
) -> None:
    """Открывает меню управления релевантными / нерелевантными фразами."""
    adv_setting_id: int = callback_data.adv_setting_original_id

    async with sm(read_only=True) as session:
        adv = await load_adv_setting_by_pk_in_session(session, adv_setting_id)

    if adv is None:
        raise RuntimeError("РR не найдена")

    assert callback_query.message is not None
    await RelevantPhraseManagementMenuMessage(
        bot,
        callback_query.message.chat.id,
        adv,
    )()


@router.callback_query(ChangeAutoAddOnlyRelevantPhraseStatus.filter())
async def toggle_auto_add_only_relevant_phrase(
    callback_query: CallbackQuery,
    callback_data: ChangeAutoAddOnlyRelevantPhraseStatus,
    bot: Bot,
) -> None:
    """Переключает auto_add_only_relevant_phrase; под A/B Hold freeze — отказ без write."""
    new_status: bool = callback_data.new_status
    adv_id: int = callback_data.adv_id

    async with sm(read_only=False) as session:
        outcome = await toggle_auto_add_only_relevant_phrase_in_session(
            session, adv_id=adv_id, new_status=new_status
        )

    if outcome.adv is None:
        return

    if outcome.blocked:
        assert isinstance(callback_query.message, Message)
        await callback_query.message.answer(AB_HOLD_AUTO_ADD_ONLY_RELEVANT_BLOCKED_MSG)
        return

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    status_str = (
        "Включено добавление только релевантных фраз"
        if new_status
        else "Выключено добавление только релевантных фраз"
    )

    await bot.send_message(chat_id, status_str)

    async with sm(read_only=True) as session:
        adv = await load_adv_by_adv_id_in_session(session, adv_id)

    if adv is None:
        return

    assert callback_query.from_user
    await RelevantPhraseManagementMenuMessage(
        bot,
        chat_id,
        adv,
    )()
