"""Telegram handlers Emergency kill switch (change ab-hold-emergency-kill-switch).

Подключается из ``telegram.handlers`` (тот же ``card_ab_hold_router``).
Делит screen helpers с Hold handlers (sibling package module).
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
    SUPPORT_LINK,
    apply_ab_hold_emergency_in_session,
    format_emergency_user_result_text,
    is_ab_hold_emergency_latch_active,
    is_ab_hold_emergency_visible,
    mark_emergency_educated_in_memory,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers as hold_handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldEmergencyAbort,
    CardAbHoldEmergencyAsk,
    CardAbHoldEmergencyConfirm,
    CardAbHoldEmergencyEducate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    is_card_ab_hold_ui_visible,
)
from app.utils.db.session_maker import get_async_session_maker as sm

EmergencyEducateAckKind = Literal["ok", "ui_hidden", "emergency_not_visible"]


@dataclass(frozen=True, slots=True)
class EmergencyEducateAckOutcome:
    """Итог PG-seam ACK образования Emergency (caller commits).

    ``kind``:
    - ``ok`` — educated выставлен на ``adv`` в сессии;
    - ``ui_hidden`` — нет AdvSetting / paid UI скрыт;
    - ``emergency_not_visible`` — Hold mode OFF (Emergency недоступен).
    """

    kind: EmergencyEducateAckKind
    adv: AdvSetting | None = None


async def acknowledge_emergency_education_in_session(
    session: AsyncSession,
    *,
    adv_setting_original_id: int,
) -> EmergencyEducateAckOutcome:
    """Загрузить AdvSetting и ACK образования Emergency в переданной WRITE session.

    Parent (``emergency_educate_ack``) открывает ``sm(read_only=False)`` и
    передаёт session сюда; commit — на вызывающем после успешного ``ok``.

    Args:
        session: открытая AsyncSession (WRITE / caller commits).
        adv_setting_original_id: PK ``AdvSetting.id``.

    Returns:
        ``EmergencyEducateAckOutcome`` с kind и опционально мутированным ``adv``.
    """
    adv = await session.get(AdvSetting, adv_setting_original_id)
    if adv is None or not is_card_ab_hold_ui_visible(adv):
        return EmergencyEducateAckOutcome(kind="ui_hidden")
    if not is_ab_hold_emergency_visible(adv.card_ab_hold_mode):
        return EmergencyEducateAckOutcome(kind="emergency_not_visible")
    mark_emergency_educated_in_memory(adv)
    return EmergencyEducateAckOutcome(kind="ok", adv=adv)


def _emergency_education_text() -> str:
    """Текст образования Emergency (spec launch education + SUPPORT_LINK)."""
    return (
        "🚨 Emergency (аварийный стоп)\n\n"
        "Если что-то сильно пошло не так — нажмите Emergency.\n"
        "Система сразу:\n"
        "• поставит РК на паузу\n"
        "• заблокирует все ключи\n"
        "• запретит пополнение бюджета\n\n"
        "Это сигнал, что нужен контакт с поддержкой.\n"
        f"Поддержка: {SUPPORT_LINK}"
    )


def _emergency_confirm_prompt_text() -> str:
    """Текст confirm перед исполнением Emergency."""
    return (
        "Точно остановить? РК на паузу, ключи в блок, бюджет не пополняется.\n"
        "Если пришлось нажать — напишите в поддержку."
    )


def _emergency_abort_ack_text() -> str:
    """Ответ callback при отмене confirm (≤200 символов Telegram)."""
    return "Emergency отменён — ничего не меняли."


def build_emergency_confirm_keyboard(adv_id: int) -> InlineKeyboardMarkup:
    """Клавиатура confirm Emergency (cancel / confirm / support URL)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, остановить траты",
                    callback_data=CardAbHoldEmergencyConfirm(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=CardAbHoldEmergencyAbort(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Связаться с поддержкой",
                    url=SUPPORT_LINK,
                )
            ],
        ]
    )


@hold_handlers.card_ab_hold_router.callback_query(CardAbHoldEmergencyEducate.filter())
async def emergency_educate_ack(
    query: CallbackQuery, callback_data: CardAbHoldEmergencyEducate
) -> None:
    """Confirm/ACK образования Emergency на Hold screen (spec launch education)."""
    async with sm(read_only=False) as session:
        outcome = await acknowledge_emergency_education_in_session(
            session,
            adv_setting_original_id=callback_data.adv_setting_original_id,
        )
        if outcome.kind == "ui_hidden":
            await hold_handlers._notify_callback_user(
                query, "Доступно только при включённом боте"
            )
            return
        if outcome.kind == "emergency_not_visible":
            await hold_handlers._notify_callback_user(
                query, "Emergency доступен только в режиме A/B Hold"
            )
            return
        adv = outcome.adv
        assert adv is not None
        await session.commit()
        mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
        status = await hold_handlers._screen_status_text(adv, mode)
        edu = _emergency_education_text()
        await hold_handlers._notify_callback_user(
            query, "Ок, Emergency доступен. Используйте только если всё плохо."
        )
        await hold_handlers._edit_screen(
            query,
            f"{edu}\n\n{hold_handlers._INSTRUCTION}\n{status}",
            adv.id,
            mode,
            phase=getattr(adv, "card_ab_hold_phase", None),
            emergency_educated=True,
            emergency_latch=is_ab_hold_emergency_latch_active(
                getattr(adv, "card_ab_hold_emergency_latch", False)
            ),
            alert_if_unavailable=False,
        )


@hold_handlers.card_ab_hold_router.callback_query(CardAbHoldEmergencyAsk.filter())
async def emergency_ask_confirm(
    query: CallbackQuery, callback_data: CardAbHoldEmergencyAsk
) -> None:
    """Показать confirm перед Emergency (spec Confirm before Emergency executes)."""
    msg = query.message
    if not isinstance(msg, Message):
        return
    adv_id = callback_data.adv_setting_original_id
    await msg.answer(
        _emergency_confirm_prompt_text(),
        reply_markup=build_emergency_confirm_keyboard(adv_id),
    )


@hold_handlers.card_ab_hold_router.callback_query(CardAbHoldEmergencyAbort.filter())
async def emergency_abort(
    query: CallbackQuery, callback_data: CardAbHoldEmergencyAbort
) -> None:
    """Отмена confirm Emergency — без мутаций."""
    _ = callback_data
    await hold_handlers._notify_callback_user(query, _emergency_abort_ack_text())


@hold_handlers.card_ab_hold_router.callback_query(CardAbHoldEmergencyConfirm.filter())
async def emergency_confirm_execute(
    query: CallbackQuery, callback_data: CardAbHoldEmergencyConfirm
) -> None:
    """Исполнить Emergency kill switch (spec stops spend + support CTA)."""
    async with sm(read_only=False) as session:
        adv = await session.get(AdvSetting, callback_data.adv_setting_original_id)
        if adv is None or not is_card_ab_hold_ui_visible(adv):
            await hold_handlers._notify_callback_user(
                query, "Доступно только при включённом боте"
            )
            return
        if not is_ab_hold_emergency_visible(adv.card_ab_hold_mode):
            await hold_handlers._notify_callback_user(
                query, "Emergency доступен только в режиме A/B Hold"
            )
            return
        result = await apply_ab_hold_emergency_in_session(
            session, adv_setting_id=adv.id
        )
        await session.commit()
        mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
        text = format_emergency_user_result_text(result)
        await hold_handlers._notify_callback_user(query, text)
        await hold_handlers._edit_screen(
            query,
            f"{text}\n\n{hold_handlers._INSTRUCTION}\nСтатус: {mode.value}",
            adv.id,
            mode,
            phase=getattr(adv, "card_ab_hold_phase", None),
            emergency_educated=True,
            emergency_latch=True,
            alert_if_unavailable=False,
        )
