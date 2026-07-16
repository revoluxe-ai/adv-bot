"""Telegram handlers экрана A/B Hold (spec ``card-ab-hold-mode``)."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    empty_allowed_snapshot,
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
    CardAbHoldSetupBlockRedisCache,
    CardAbHoldSignalKind,
    CardAbHoldSignalRedisCache,
    CardAbHoldSignalSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldBack,
    CardAbHoldCancel,
    CardAbHoldDisable,
    CardAbHoldEnable,
    CardAbHoldLaunchAnyway,
    CardAbHoldMenu,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stats_enable_gate import (
    build_ab_hold_enable_blocked_alert,
    build_ab_hold_enable_blocked_by_stats_message,
    evaluate_ab_hold_enable_stats,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.launch_validity_gate import (
    build_ab_hold_low_views_alert,
    build_ab_hold_low_views_warning_message,
    build_ab_hold_views_unavailable_alert,
    build_ab_hold_views_unavailable_message,
    evaluate_ab_hold_launch_view_volume,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    can_enable_card_ab_hold,
    can_enable_card_ab_hold_on_version,
    card_ab_hold_enable_noop_answer,
    card_ab_hold_requires_max_cpo_message,
    card_ab_hold_requires_v3_message,
    has_positive_plan_max_cpo,
    is_card_ab_hold_enable_noop,
    is_card_ab_hold_ui_visible,
    should_offer_card_ab_hold_enable_control,
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
    "остальные OFF; ЦП = текущая позиция; разрешённый набор фраз фиксируется.\n"
    "HOLD: обновление ЦП выкл, биддер продолжает работать.\n"
    "Во время A/B Hold набор рекламных фраз зафиксирован: новые фразы "
    "автоматически исключаются, а ручные изменения в кабинете WB могут быть "
    "возвращены ботом к зафиксированному набору. Чтобы изменить набор фраз, "
    "отключите A/B Hold. Для РК с открытым матчингом или при большом числе "
    "фраз (лимит минус-слов WB) чистота фиксации не гарантируется полностью.\n"
    "EXIT: снова обновление ЦП, апдейтеры и минус-фраз (без restore профиля ключей).\n"
)


def _screen_keyboard(
    adv_id: int, mode: CardAbHoldMode | str | None
) -> InlineKeyboardMarkup:
    """Клавиатура экрана A/B Hold (decision §11).

    Enable — только при ``OFF``; при PENDING/ACTIVE кнопка скрыта.
    Disable и Back всегда. Handler Enable при stale callback — §10 no-op.
    """
    rows: list[list[InlineKeyboardButton]] = []
    if should_offer_card_ab_hold_enable_control(mode):
        rows.append(
            [
                InlineKeyboardButton(
                    text="Включить режим A/B",
                    callback_data=CardAbHoldEnable(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Выключить режим A/B",
                callback_data=CardAbHoldDisable(
                    adv_setting_original_id=adv_id
                ).pack(),
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="← Назад",
                callback_data=CardAbHoldBack(
                    adv_setting_original_id=adv_id
                ).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _edit_screen(
    query: CallbackQuery,
    text: str,
    adv_id: int,
    mode: CardAbHoldMode | str | None,
) -> None:
    """Редактировать message экрана, если это доступный ``Message``."""
    msg = query.message
    if isinstance(msg, Message):
        await msg.edit_text(
            text, reply_markup=_screen_keyboard(adv_id, mode)
        )


async def _screen_status_text(
    adv: AdvSetting, mode: CardAbHoldMode
) -> str:
    """Текст статуса для экрана A/B Hold (decision §14b).

    Для ``PENDING_SETUP`` показывает actionable-причину детерминированного блока
    setup (пустой allowed-set / нет плана max CPO) из Redis-канала
    ``CardAbHoldSetupBlock`` — кампания не должна молча висеть в вечном PENDING
    (spec «PENDING_SETUP setup blockers are surfaced and recoverable»). Для прочих
    режимов — краткий статус (готовность теста — только ACTIVE, decision §8).
    """
    if mode != CardAbHoldMode.PENDING_SETUP:
        return f"Статус: {mode.value}"
    block = await CardAbHoldSetupBlockRedisCache(adv).get_block()
    return build_enter_poll_status_lines(
        mode=mode,
        abort_safe=None,
        abort_can_continue=None,
        degraded=bool(getattr(adv, "card_ab_hold_degraded", False)),
        block_kind=block.kind if block is not None else None,
    )


def _low_views_warning_keyboard(adv_id: int) -> InlineKeyboardMarkup:
    """Клавиатура soft-warning низкого объёма показов (decision §2c).

    «Всё равно запустить» → ENTER (пользователь принял риск); «Отмена» →
    остаётся ``OFF``, ENTER не пишется.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Всё равно запустить",
                    callback_data=CardAbHoldLaunchAnyway(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=CardAbHoldCancel(
                        adv_setting_original_id=adv_id
                    ).pack(),
                )
            ],
        ]
    )


async def _edit_low_views_warning(
    query: CallbackQuery, text: str, adv_id: int
) -> None:
    """Показать soft-warning объёма с выбором «запустить / отмена» (§2c)."""
    msg = query.message
    if isinstance(msg, Message):
        await msg.edit_text(
            text, reply_markup=_low_views_warning_keyboard(adv_id)
        )


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
        status = await _screen_status_text(adv, mode)
        await _edit_screen(query, f"{_INSTRUCTION}\n{status}", adv.id, mode)
        await query.answer()


async def _handle_ab_hold_enable(
    query: CallbackQuery,
    adv_setting_original_id: int,
    *,
    skip_view_volume_gate: bool,
) -> None:
    """Общий enable-путь ENTER для кнопок «Включить» и «Всё равно запустить».

    Spec card-ab-hold-mode / decision write-path:
    §2a — при проблемной стате enable no-op, причина + ограничение + ``SUPPORT_LINK``;
    §2c — при низком measured объёме (calendar-day MV cover) soft-warning с выбором
    (mode остаётся ``OFF``); при CH error — distinct soft reason без low-impressions
    copy; ``skip_view_volume_gate=True`` — пользователь уже подтвердил запуск
    «на свой риск», объёмный гейт пропускается (остальные gates перепроверяются
    на случай stale callback);
    §10 / Enable idempotent — PENDING/ACTIVE → no demote, no ENTER rewrite;
    §12 — только V3. Immediate setup job out of MVP: UI показывает PENDING и poll
    LastAbort/ACTIVE.
    """
    async with sm() as session:
        adv = await session.scalar(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        if adv is None or not can_enable_card_ab_hold(adv):
            await query.answer("Доступно только при включённом боте", show_alert=True)
            return
        if is_card_ab_hold_enable_noop(adv):
            mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
            await query.answer(card_ab_hold_enable_noop_answer(adv), show_alert=True)
            await _edit_screen(
                query, f"{_INSTRUCTION}\nСтатус: {mode.value}", adv.id, mode
            )
            logger.info(
                "[adv_id=%s] CardAbHold Enable no-op (already %s)",
                adv.adv_id,
                mode.value,
            )
            return
        if not can_enable_card_ab_hold_on_version(adv):
            reason = card_ab_hold_requires_v3_message()
            await query.answer(reason, show_alert=True)
            await _edit_screen(
                query,
                f"{_INSTRUCTION}\n{reason}",
                adv.id,
                CardAbHoldMode.OFF,
            )
            logger.info(
                "[adv_id=%s] CardAbHold Enable blocked: not V3 (automatic_version=%s)",
                adv.adv_id,
                getattr(adv, "automatic_version", None),
            )
            return
        if not has_positive_plan_max_cpo(adv):
            reason = card_ab_hold_requires_max_cpo_message()
            await query.answer(reason, show_alert=True)
            await _edit_screen(
                query,
                f"{_INSTRUCTION}\n{reason}",
                adv.id,
                CardAbHoldMode.OFF,
            )
            logger.info(
                "[adv_id=%s] CardAbHold Enable blocked: plan max CPO missing/≤0 "
                "(max_price_for_order=%s)",
                adv.adv_id,
                getattr(adv, "max_price_for_order", None),
            )
            return
        stats_ok, stats_reason = await evaluate_ab_hold_enable_stats(adv)
        if not stats_ok:
            blocked = build_ab_hold_enable_blocked_by_stats_message(stats_reason)
            await query.answer(
                build_ab_hold_enable_blocked_alert(stats_reason),
                show_alert=True,
            )
            await _edit_screen(
                query,
                f"{_INSTRUCTION}\n{blocked}",
                adv.id,
                CardAbHoldMode.OFF,
            )
            return
        if not skip_view_volume_gate:
            volume_eval = await evaluate_ab_hold_launch_view_volume(adv)
            if volume_eval.is_unavailable:
                await query.answer(
                    build_ab_hold_views_unavailable_alert(), show_alert=True
                )
                await _edit_screen(
                    query,
                    f"{_INSTRUCTION}\n{build_ab_hold_views_unavailable_message()}",
                    adv.id,
                    CardAbHoldMode.OFF,
                )
                logger.info(
                    "[adv_id=%s] CardAbHold Enable volume stats unavailable (CH)",
                    adv.adv_id,
                )
                return
            if not volume_eval.is_sufficient:
                total_views = volume_eval.total_views
                await query.answer(
                    build_ab_hold_low_views_alert(total_views), show_alert=True
                )
                await _edit_low_views_warning(
                    query,
                    build_ab_hold_low_views_warning_message(total_views),
                    adv.id,
                )
                logger.info(
                    "[adv_id=%s] CardAbHold Enable low measured views=%s → warn+choice",
                    adv.adv_id,
                    total_views,
                )
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
            degraded=bool(getattr(adv, "card_ab_hold_degraded", False)),
        )
        logger.info("[adv_id=%s] CardAbHold ENTER → PENDING_SETUP", adv.adv_id)
        await query.answer("Подготовка A/B Hold…")
        await _edit_screen(
            query,
            f"{_INSTRUCTION}\n{status}",
            adv.id,
            normalize_card_ab_hold_mode(adv.card_ab_hold_mode),
        )


@card_ab_hold_router.callback_query(CardAbHoldEnable.filter())
async def enable_card_ab_hold(
    query: CallbackQuery, callback_data: CardAbHoldEnable
) -> None:
    """Кнопка «Включить»: ENTER с полным набором gates, включая §2c объём (MV cover)."""
    await _handle_ab_hold_enable(
        query, callback_data.adv_setting_original_id, skip_view_volume_gate=False
    )


@card_ab_hold_router.callback_query(CardAbHoldLaunchAnyway.filter())
async def launch_card_ab_hold_anyway(
    query: CallbackQuery, callback_data: CardAbHoldLaunchAnyway
) -> None:
    """§2c «Всё равно запустить»: ENTER несмотря на низкий объём показов.

    Пользователь осознанно принял риск слабого A/B: объёмный soft-gate
    пропускается, остальные gates (bot_active/no-op/V3/freshness) перепроверяются
    на случай stale callback.
    """
    await _handle_ab_hold_enable(
        query, callback_data.adv_setting_original_id, skip_view_volume_gate=True
    )


@card_ab_hold_router.callback_query(CardAbHoldCancel.filter())
async def cancel_card_ab_hold_enable(
    query: CallbackQuery, callback_data: CardAbHoldCancel
) -> None:
    """§2c «Отмена» soft-warning объёма: mode остаётся OFF, ENTER не пишется."""
    async with sm() as session:
        adv = await session.scalar(
            select(AdvSetting).where(AdvSetting.id == callback_data.adv_setting_original_id)
        )
        if adv is None or not is_card_ab_hold_ui_visible(adv):
            await query.answer("Доступно только при включённом боте", show_alert=True)
            return
        mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
        logger.info(
            "[adv_id=%s] CardAbHold Enable cancelled at low-views warning (mode=%s)",
            adv.adv_id,
            mode.value,
        )
        await query.answer("Включение отменено")
        await _edit_screen(
            query, f"{_INSTRUCTION}\nСтатус: {mode.value}", adv.id, mode
        )


@card_ab_hold_router.callback_query(CardAbHoldDisable.filter())
async def disable_card_ab_hold(
    query: CallbackQuery, callback_data: CardAbHoldDisable
) -> None:
    """EXIT: OFF + clear allowed-set snapshot + cleanup signal (spec §8, без keyword restore)."""
    async with sm() as session:
        adv = await session.scalar(
            select(AdvSetting).where(AdvSetting.id == callback_data.adv_setting_original_id)
        )
        if adv is None or not is_card_ab_hold_ui_visible(adv):
            await query.answer("Доступно только при включённом боте", show_alert=True)
            return
        adv.card_ab_hold_mode = CardAbHoldMode.OFF.value
        adv.card_ab_hold_allowed_phrases_snapshot = empty_allowed_snapshot()
        await session.commit()
        cache = CardAbHoldSignalRedisCache(adv)
        await cache.clear()
        # decision §14c: EXIT — путь восстановления из зависшего PENDING; снимаем и
        # причину блока setup, чтобы стало ясно — ordinary automation снова активна.
        await CardAbHoldSetupBlockRedisCache(adv).clear()
        logger.info(
            "[adv_id=%s] CardAbHold EXIT → OFF (allowed-set snapshot cleared)", adv.adv_id
        )
        await query.answer("Режим A/B выключен")
        await _edit_screen(
            query, f"{_INSTRUCTION}\nСтатус: off", adv.id, CardAbHoldMode.OFF
        )


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
