"""Telegram handlers экрана A/B Hold (spec ``card-ab-hold-mode``)."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    empty_minus_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.enter_status import (
    build_enter_poll_status_lines,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    CardAbHoldLastAbortRedisCache,
    CardAbHoldSignalKind,
    CardAbHoldSignalRedisCache,
    CardAbHoldSignalSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldBack,
    CardAbHoldDisable,
    CardAbHoldEnable,
    CardAbHoldMenu,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stats_enable_gate import (
    build_ab_hold_enable_blocked_alert,
    build_ab_hold_enable_blocked_by_stats_message,
    evaluate_ab_hold_enable_stats,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    can_enable_card_ab_hold,
    card_ab_hold_enable_noop_answer,
    is_card_ab_hold_enable_noop,
    is_card_ab_hold_ui_visible,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

card_ab_hold_router = Router(name="card_ab_hold")

_INSTRUCTION = (
    "Режим A/B тестирования карточки\n\n"
    "Перед включением:\n"
    "• прогрейте РК с не зажатым max CPO и запасом плана продаж (шт.);\n"
    "• рекомендуется выключить полки (если без них нет трафика — на ваше усмотрение);\n"
    "• не меняйте цену на период теста.\n\n"
    "ENTER: ключи с pay_for_order ≤ max CPO и ≥100 показов остаются; "
    "остальные OFF; ЦП = текущая позиция; минус-фразы синхронизируются и "
    "фиксируются.\n"
    "HOLD: обновление ЦП выкл, биддер продолжает работать.\n"
    "Во время A/B Hold минус-фразы фиксируются. Ручные изменения в кабинете WB "
    "могут быть возвращены ботом к зафиксированному состоянию. "
    "Чтобы изменить минус-фразы, отключите A/B Hold.\n"
    "EXIT: снова обновление ЦП, апдейтеры и минус-фраз (без restore профиля ключей).\n"
)


def _screen_keyboard(adv_id: int) -> InlineKeyboardMarkup:
    """Клавиатура экрана A/B Hold (вкл / выкл / назад)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Включить режим A/B",
                    callback_data=CardAbHoldEnable(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Выключить режим A/B",
                    callback_data=CardAbHoldDisable(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=CardAbHoldBack(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ],
        ]
    )


async def _edit_screen(query: CallbackQuery, text: str, adv_id: int) -> None:
    """Редактировать message экрана, если это доступный ``Message``."""
    msg = query.message
    if isinstance(msg, Message):
        await msg.edit_text(text, reply_markup=_screen_keyboard(adv_id))


@card_ab_hold_router.callback_query(CardAbHoldMenu.filter())
async def open_card_ab_hold_menu(
    query: CallbackQuery, callback_data: CardAbHoldMenu
) -> None:
    """Открыть инструкцию A/B Hold (spec card-ab-hold-mode paid-only UI)."""
    async with sm() as session:
        adv = await session.scalar(
            select(AdvSetting).where(AdvSetting.id == callback_data.adv_setting_original_id)
        )
        if adv is None or not is_card_ab_hold_ui_visible(adv):
            await query.answer("Доступно только при включённом боте", show_alert=True)
            return
        mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
        await _edit_screen(query, f"{_INSTRUCTION}\nСтатус: {mode.value}", adv.id)
        await query.answer()


@card_ab_hold_router.callback_query(CardAbHoldEnable.filter())
async def enable_card_ab_hold(
    query: CallbackQuery, callback_data: CardAbHoldEnable
) -> None:
    """ENTER: gate bot_active + stats freshness, PG PENDING_SETUP, Redis ENTER.

    Spec card-ab-hold-mode / decision write-path §2a: при проблемной стате —
    enable no-op, сразу причина + ограничение + ``SUPPORT_LINK``.
    Decision §10 / Enable idempotent: PENDING/ACTIVE → no demote, no ENTER rewrite.
    Immediate setup job out of MVP — UI показывает PENDING и poll LastAbort/ACTIVE.
    """
    async with sm() as session:
        adv = await session.scalar(
            select(AdvSetting).where(AdvSetting.id == callback_data.adv_setting_original_id)
        )
        if adv is None or not can_enable_card_ab_hold(adv):
            await query.answer("Доступно только при включённом боте", show_alert=True)
            return
        if is_card_ab_hold_enable_noop(adv):
            mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
            await query.answer(card_ab_hold_enable_noop_answer(adv), show_alert=True)
            await _edit_screen(
                query, f"{_INSTRUCTION}\nСтатус: {mode.value}", adv.id
            )
            logger.info(
                "[adv_id=%s] CardAbHold Enable no-op (already %s)",
                adv.adv_id,
                mode.value,
            )
            return
        stats_ok, stats_reason = await evaluate_ab_hold_enable_stats(adv)
        if not stats_ok:
            blocked = build_ab_hold_enable_blocked_by_stats_message(stats_reason)
            await query.answer(
                build_ab_hold_enable_blocked_alert(stats_reason),
                show_alert=True,
            )
            await _edit_screen(query, f"{_INSTRUCTION}\n{blocked}", adv.id)
            return
        adv.card_ab_hold_mode = CardAbHoldMode.PENDING_SETUP.value
        await session.commit()
        await CardAbHoldSignalRedisCache(adv).set_signal(
            CardAbHoldSignalSnapshot(signal=CardAbHoldSignalKind.ENTER)
        )
        abort = await CardAbHoldLastAbortRedisCache(adv).get_abort()
        await session.refresh(adv)
        status = build_enter_poll_status_lines(
            mode=adv.card_ab_hold_mode,
            abort_safe=abort.safe if abort is not None else None,
            abort_can_continue=abort.can_continue if abort is not None else None,
        )
        logger.info("[adv_id=%s] CardAbHold ENTER → PENDING_SETUP", adv.adv_id)
        await query.answer("Подготовка A/B Hold…")
        await _edit_screen(query, f"{_INSTRUCTION}\n{status}", adv.id)


@card_ab_hold_router.callback_query(CardAbHoldDisable.filter())
async def disable_card_ab_hold(
    query: CallbackQuery, callback_data: CardAbHoldDisable
) -> None:
    """EXIT: OFF + clear minus snapshot + cleanup signal (spec §8, без keyword restore)."""
    async with sm() as session:
        adv = await session.scalar(
            select(AdvSetting).where(AdvSetting.id == callback_data.adv_setting_original_id)
        )
        if adv is None or not is_card_ab_hold_ui_visible(adv):
            await query.answer("Доступно только при включённом боте", show_alert=True)
            return
        adv.card_ab_hold_mode = CardAbHoldMode.OFF.value
        adv.card_ab_hold_minus_phrases_snapshot = empty_minus_snapshot()
        await session.commit()
        cache = CardAbHoldSignalRedisCache(adv)
        await cache.clear()
        logger.info("[adv_id=%s] CardAbHold EXIT → OFF (minus snapshot cleared)", adv.adv_id)
        await query.answer("Режим A/B выключен")
        await _edit_screen(query, f"{_INSTRUCTION}\nСтатус: off", adv.id)


@card_ab_hold_router.callback_query(CardAbHoldBack.filter())
async def back_from_card_ab_hold(
    query: CallbackQuery, callback_data: CardAbHoldBack
) -> None:
    """Закрыть экран A/B Hold (пользователь возвращается в меню РК вручную)."""
    _ = callback_data
    await query.answer()
    msg = query.message
    if isinstance(msg, Message):
        await msg.edit_text(
            "Экран A/B Hold закрыт. Откройте меню рекламной кампании снова."
        )
