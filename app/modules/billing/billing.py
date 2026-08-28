"""Billing per-cabinet daily charges with Redis/DB dedup and Redis locks (без pg_advisory_lock)."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Coroutine

CabinetProcessResult = dict[str, int | bool | str | float | None]

from dependency_injector.wiring import inject, Provide
from sqlalchemy import exists, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client_bot.notification_sender import get_notification_sender
from app.client_bot.user_interface.services.auto_management_mode import (
    apply_free_mode_transition,
)
from app.modules.billing.event_manager.event_manager import BillingEventManager

from app.modules.billing.di import BillingContainer
from app.modules.billing.leg_metering import (
    compute_cabinet_billable_units,
    record_anchor_latch_samples,
    resolve_metering_anchors,
)
from app.modules.billing.models import AdvPayment, AdvPaymentLegType
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
    WBBalancePayment,
    WBBonusPayment,
)
from app.utils.db.session_maker import get_async_session_maker as sm
from app.utils.db.models import User
from .redis_lock import RedisLock
from .redis_manager import RedisManager
from ..common_slaves.wildberries.models.wb_cabinet import WBCabinet

logger = logging.getLogger(__name__)


async def _fetch_active_cabinet_ids(session: AsyncSession) -> list[int]:
    """Вернуть id кабинетов, у которых есть активные кампании.
    Используем только id чтобы потом загружать свежие данные в отдельных коротких транзакциях.
    """
    stmt = select(WBCabinet.id).where(
        exists(
            select(1).where(
                AdvSetting.wb_cabinet_id == WBCabinet.id, AdvSetting.bot_active
            )
        )
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def _load_cabinet_with_relations(
    session: AsyncSession, cabinet_id: int
) -> WBCabinet | None:
    """Подгрузить кабинет со связанными выплатами/кампаниями (актуальные данные)."""
    stmt = (
        select(WBCabinet)
        .options(
            selectinload(WBCabinet.balance_payments),
            selectinload(WBCabinet.bonus_payments),
            selectinload(WBCabinet.adv_settings).selectinload(AdvSetting.payments),
        )
        .where(WBCabinet.id == cabinet_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


GRACE_MAX_NEGATIVE_DAYS = 7  # множитель к дневному расходу: в минус можно не более 7× price_for_day

GRACE_EXCEEDED_MESSAGE = (
    "Кампании отключены: превышен допустимый минус по балансу (лимит 7 дней расхода). "
    "Пополните баланс, чтобы снова включить управление рекламой."
)


async def _load_cabinet_user_chats(
    session: AsyncSession,
    cabinet_id: int,
) -> list[tuple[int, int | None]]:
    """Загрузить Telegram ID пользователей кабинета в переданной PG-сессии."""
    stmt = (
        select(User.id, User.user_telegram_id)
        .select_from(WBUserCabinet)
        .join(User, User.id == WBUserCabinet.user_id)
        .where(
            WBUserCabinet.wb_cabinet_id == cabinet_id,
            User.user_telegram_id.is_not(None),
        )
    )
    result = await session.execute(stmt)
    return [
        (int(user_id), int(chat_id) if chat_id is not None else None)
        for user_id, chat_id in result.all()
    ]


def _days_until_block_message(days_left: int) -> str:
    """Склонение: 1 день / 2-4 дня / 5-20 дней / 21 день / ..."""
    if days_left % 10 == 1 and days_left % 100 != 11:
        return "день"
    if days_left % 10 in (2, 3, 4) and days_left % 100 not in (12, 13, 14):
        return "дня"
    return "дней"


async def _notify_days_until_block(cabinet_id: int, days_left: int) -> None:
    """Отправить пользователям кабинета: ежедневное списание выполнено, осталось N дней до полной блокировки."""
    word = _days_until_block_message(days_left)
    text = (
        f"Ежедневное списание выполнено. До полной блокировки осталось {days_left} {word}."
    )
    sender = get_notification_sender()
    async with sm(read_only=True) as session:
        rows = await _load_cabinet_user_chats(session, cabinet_id)
    for _user_id, chat_id in rows:
        if chat_id is None:
            continue
        try:
            _ = await sender.send_message(int(chat_id), text)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Days until block notification failed for cabinet %s chat %s: %s",
                cabinet_id,
                chat_id,
                exc,
            )


async def _notify_grace_exceeded(cabinet_id: int) -> None:
    """Отправить уведомление пользователям кабинета об отключении из-за превышения лимита минуса."""
    event_manager = BillingEventManager()
    sender = get_notification_sender()
    async with sm(read_only=True) as session:
        rows = await _load_cabinet_user_chats(session, cabinet_id)
    for user_id, chat_id in rows:
        if chat_id is None:
            continue
        try:
            success = await sender.send_message(int(chat_id), GRACE_EXCEEDED_MESSAGE)
            if success:
                async with sm(read_only=False) as session:
                    await event_manager.emit_balance_grace_exceeded_sent(
                        user_id=user_id,
                        user_telegram_id=int(chat_id),
                        wb_cabinet_id=cabinet_id,
                        session=session,
                    )
                    await session.commit()
            else:
                async with sm(read_only=False) as session:
                    await event_manager.emit_balance_grace_exceeded_failed(
                        user_id=user_id,
                        user_telegram_id=int(chat_id),
                        wb_cabinet_id=cabinet_id,
                        error="send_message returned False",
                        session=session,
                    )
                    await session.commit()
        except Exception as exc:
            logger.warning(
                "Grace exceeded notification failed for cabinet %s user %s: %s",
                cabinet_id,
                user_id,
                exc,
                exc_info=True,
            )
            try:
                async with sm(read_only=False) as session:
                    await event_manager.emit_balance_grace_exceeded_failed(
                        user_id=user_id,
                        user_telegram_id=int(chat_id) if chat_id else None,
                        wb_cabinet_id=cabinet_id,
                        error=str(exc),
                        session=session,
                    )
                    await session.commit()
            except Exception as emit_exc:
                logger.warning("Emit grace_exceeded_failed failed: %s", emit_exc)


async def _anchor_has_adv_payment_for_day(
    session: AsyncSession, anchor_id: int, day: date
) -> bool:
    """Legacy-tolerant: любая AdvPayment за якорь и UTC-день блокирует повтор."""
    count = await session.scalar(
        select(func.count()).where(
            and_(
                AdvPayment.adv_setting_id == anchor_id,
                AdvPayment.date == day,
            )
        )
    )
    return bool(count and count > 0)


async def _adv_payment_type_exists(
    session: AsyncSession, anchor_id: int, day: date, payment_type: str
) -> bool:
    count = await session.scalar(
        select(func.count()).where(
            and_(
                AdvPayment.adv_setting_id == anchor_id,
                AdvPayment.date == day,
                AdvPayment.type == payment_type,
            )
        )
    )
    return bool(count and count > 0)


async def _safe_commit(
    session: AsyncSession,
    result: dict[str, int | bool | str | float | None],
    cabinet_id: int,
) -> bool:
    """Безопасный commit: при ошибке логирует, делает rollback и проставляет reason.
    Возвращает True при успехе, False при ошибке (result['reason'] уже задан).
    """
    try:
        await session.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        logger.error("Cabinet %s: commit error: %s", cabinet_id, exc, exc_info=True)
        result["reason"] = "db_commit_error"
        return False


async def _process_single_cabinet(
    cabinet_id: int,
    current_dt: datetime,
    pricer: Pricer,
    redis_manager: RedisManager,
    skip_by_redis: bool = True
) -> dict[str, int | bool | str | float | None]:
    async with sm(read_only=False) as session:
        return await __process_single_cabinet(
            session=session,
            cabinet_id=cabinet_id,
            current_dt=current_dt,
            pricer=pricer,
            redis_manager=redis_manager,
            skip_by_redis=skip_by_redis
        )


async def __process_single_cabinet(
    session: AsyncSession,
    cabinet_id: int,
    current_dt: datetime,
    pricer: Pricer,
    redis_manager: RedisManager,
    skip_by_redis: bool = True,
) -> dict[str, int | bool | str | float | None]:
    """Обработать один кабинет в отдельной короткой транзакции.

    Возвращает словарь c результатом:
      {
        'cabinet_id': int,
        'processed': bool,            # была ли попытка списания средств
        'payment_successful': bool,   # произведено списание
        'reason': str,                # причина пропуска / успеха
        'campaigns': int,             # число активных кампаний (на момент обработки)
        'price_for_day': float | None
      }
    Идемпотентность обеспечивается проверками в БД + Redis-флагом.
    Порядок: загрузка кабинета -> проверка списаний в БД -> latch sample ->
    charge -> commit -> Redis-флаг только на терминальных путях (debit / already_processed_db).
    Redis-флаг – ускоритель, а не источник истины: no_active/zero_price MUST NOT
    выставлять billing:processed; stale флаг MUST NOT блокировать charge без debit в БД.
    """
    result: dict[str, int | bool | str | float | None] = {
        "cabinet_id": cabinet_id,
        "processed": False,
        "payment_successful": False,
        "reason": "",
        "campaigns": 0,
        "price_for_day": None,
    }

    grace_exceeded_cabinet_id: int | None = None
    days_until_block_notify: tuple[int, int] | None = None  # (cabinet_id, days_left)
    try:
        wb_cabinet = await _load_cabinet_with_relations(session, cabinet_id)
        if wb_cabinet is None:
            result["reason"] = "cabinet_not_found"
            await session.rollback()
            return result

        cabinet_campaigns: list[AdvSetting] = [
            adv for adv in wb_cabinet.adv_settings if adv.bot_active
        ]
        result["campaigns"] = len(cabinet_campaigns)
        if not cabinet_campaigns:
            # bot_active может включиться позже в тот же UTC-день — не ставим billing:processed
            await session.commit()
            result["reason"] = "no_active_campaigns"
            return result

        day = current_dt.date()
        day_start = datetime.combine(day, datetime.min.time())
        next_day = day_start + timedelta(days=1)

        # Проверка уже существующих списаний
        bonus_count = (
            await session.scalar(
                select(func.count(WBBonusPayment.id)).where(
                    and_(
                        WBBonusPayment.wb_cabinet_id == cabinet_id,
                        WBBonusPayment.transaction_date_time >= day_start,
                        WBBonusPayment.transaction_date_time < next_day,
                        WBBonusPayment.operation_type == "auto_subtract",
                        WBBonusPayment.amount < 0,
                    )
                )
            )
        ) or 0
        balance_count = (
            await session.scalar(
                select(func.count(WBBalancePayment.id)).where(
                    and_(
                        WBBalancePayment.wb_cabinet_id == cabinet_id,
                        WBBalancePayment.transaction_date_time >= day_start,
                        WBBalancePayment.transaction_date_time < next_day,
                        WBBalancePayment.operation_type == "auto_subtract",
                        WBBalancePayment.amount < 0,
                    )
                )
            )
        ) or 0
        if bonus_count > 0 or balance_count > 0:
            await session.commit()
            try:
                await redis_manager.set_billing_process_for_day(cabinet_id, current_dt)
            except Exception as exc:
                logger.error(f"Ошибка устанвоки значения в Redis {exc}")  # noqa: BLE001
                pass
            result["reason"] = "already_processed_db"
            return result

        cabinet_adv_settings: list[AdvSetting] = list(wb_cabinet.adv_settings)
        leg_latch = redis_manager.leg_latch()
        metering_anchors = resolve_metering_anchors(cabinet_adv_settings)
        await record_anchor_latch_samples(metering_anchors, leg_latch, day)

        try:
            tariff_details = await pricer.get_tariff_details(
                session,
                wb_cabinet.shop_id,
                leg_latch=leg_latch,
                utc_date=day,
                cabinet_adv_settings=cabinet_adv_settings,
            )
            price_for_shop_for_day = tariff_details.total_per_day
        except Exception as exc:
            logger.error(
                "Cabinet %s: ошибка получения цены: %s", cabinet_id, exc, exc_info=True
            )
            raise exc

        effective_count, _anchors, billables = await compute_cabinet_billable_units(
            cabinet_adv_settings,
            latch=leg_latch,
            utc_date=day,
        )

        result["price_for_day"] = price_for_shop_for_day
        if price_for_shop_for_day <= 0:
            # Ноги могут активироваться позже в UTC-день — latch уже sampled, charge позже
            result["reason"] = "zero_price"
            return result

        calculated_bonus = float(wb_cabinet.calculated_bonus or 0)  # type: ignore[truthy-function]
        calculated_balance = float(wb_cabinet.calculated_balance or 0)  # type: ignore[truthy-function]
        payment_successful = False
        # Не сбрасываем balance_went_negative_at до оплаты: иначе минимальное
        # пополнение (total >= 0, но < price) обнулит счётчик грации.

        def add_bonus(amt: float) -> None:
            session.add(
                WBBonusPayment(
                    amount=-amt,
                    description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {day}",
                    operation_type="auto_subtract",
                    transaction_date_time=current_dt,
                    wb_cabinet=wb_cabinet,
                )
            )

        def add_balance(amt: float) -> None:
            session.add(
                WBBalancePayment(
                    amount=-amt,
                    description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {day}",
                    operation_type="auto_subtract",
                    transaction_date_time=current_dt,
                    wb_cabinet=wb_cabinet,
                )
            )

        # Логика списания
        if calculated_bonus >= price_for_shop_for_day:
            add_bonus(price_for_shop_for_day)
            payment_successful = True
        elif calculated_balance >= price_for_shop_for_day:
            add_balance(price_for_shop_for_day)
            payment_successful = True
        elif calculated_bonus + calculated_balance >= price_for_shop_for_day:
            remaining = price_for_shop_for_day
            if calculated_bonus > 0:
                use_b = min(calculated_bonus, remaining)
                add_bonus(use_b)
                remaining -= use_b
            if remaining > 0:
                add_balance(remaining)
            payment_successful = True
        else:
            # Недостаточно средств: лимит минуса = 7× дневной расход; при превышении — деактивация
            max_allowed_negative = price_for_shop_for_day * GRACE_MAX_NEGATIVE_DAYS
            balance_after_charge = (
                calculated_bonus + calculated_balance - price_for_shop_for_day
            )
            now_utc = current_dt if current_dt.tzinfo else current_dt.replace(tzinfo=timezone.utc)

            if balance_after_charge < -max_allowed_negative:
                # Превышен лимит минуса — деактивируем кампании, не списываем, не сбрасываем neg_at
                grace_exceeded_cabinet_id = cabinet_id
                # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
                for campaign in wb_cabinet.adv_settings:
                    if campaign.bot_active:
                        apply_free_mode_transition(campaign, wb_cabinet)
            else:
                # В пределах лимита: списание в минус
                if getattr(wb_cabinet, "balance_went_negative_at", None) is None:
                    wb_cabinet.balance_went_negative_at = now_utc  # type: ignore[attr-defined]
                use_b = min(calculated_bonus, price_for_shop_for_day)
                use_bal = min(max(0, calculated_balance), price_for_shop_for_day - use_b)
                shortfall = price_for_shop_for_day - use_b - use_bal
                if use_b > 0:
                    add_bonus(use_b)
                total_balance_debit = use_bal + shortfall
                if total_balance_debit > 0:
                    add_balance(total_balance_debit)
                payment_successful = True
                # Уведомление «осталось N дней до полной блокировки»
                room = balance_after_charge + max_allowed_negative
                days_left = max(0, int(room // price_for_shop_for_day))
                days_until_block_notify = (cabinet_id, days_left)

        if payment_successful:
            # После успешного списания баланс >= 0 — сбрасываем грацию минуса
            total_after = calculated_bonus + calculated_balance - price_for_shop_for_day
            if total_after >= 0:
                wb_cabinet.balance_went_negative_at = None  # type: ignore[attr-defined]
            if effective_count > 0:
                for billable in billables:
                    if await _anchor_has_adv_payment_for_day(
                        session, billable.anchor_id, day
                    ):
                        continue
                    if billable.auto_weight > 0 and not await _adv_payment_type_exists(
                        session,
                        billable.anchor_id,
                        day,
                        AdvPaymentLegType.AUTO_LEG.value,
                    ):
                        session.add(
                            AdvPayment(
                                date=day,
                                adv_setting_id=billable.anchor_id,
                                amount=price_for_shop_for_day
                                * (billable.auto_weight / effective_count),
                                type=AdvPaymentLegType.AUTO_LEG.value,
                            )
                        )
                    if (
                        billable.has_search_slot
                        and billable.search_weight > 0
                        and not await _adv_payment_type_exists(
                            session,
                            billable.anchor_id,
                            day,
                            AdvPaymentLegType.SEARCH_LEG.value,
                        )
                    ):
                        session.add(
                            AdvPayment(
                                date=day,
                                adv_setting_id=billable.anchor_id,
                                amount=price_for_shop_for_day
                                * (billable.search_weight / effective_count),
                                type=AdvPaymentLegType.SEARCH_LEG.value,
                            )
                        )

        # Фиксация БД (укороченный helper)
        if not await _safe_commit(session, result, cabinet_id):
            return result

        if grace_exceeded_cabinet_id is not None:
            try:
                await _notify_grace_exceeded(grace_exceeded_cabinet_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Cabinet %s: notify_grace_exceeded failed: %s",
                    grace_exceeded_cabinet_id,
                    exc,
                )

        if days_until_block_notify is not None:
            try:
                await _notify_days_until_block(
                    days_until_block_notify[0], days_until_block_notify[1]
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Cabinet %s: notify_days_until_block failed: %s",
                    days_until_block_notify[0],
                    exc,
                )

        # Отметка времени последнего успешного списания (best-effort, по shop_id)
        if payment_successful:
            try:
                await redis_manager.set_last_charge_at(
                    wb_cabinet.shop_id,  # type: ignore[arg-type]
                    current_dt,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Cabinet %s: не удалось записать last_charge_at в Redis: %s",
                    cabinet_id,
                    exc,
                )

        # Флаг в Redis (best-effort)
        try:
            await redis_manager.set_billing_process_for_day(cabinet_id, current_dt)
        except Exception:  # noqa
            logger.warning(
                "Cabinet %s: commit успешен, но Redis-флаг не установлен (повтор допустим)",
                cabinet_id,
            )

        result["processed"] = True
        result["payment_successful"] = payment_successful
        result["reason"] = (
            "success"
            if payment_successful
            else (
                "deactivated"
                if not payment_successful
                and calculated_bonus + calculated_balance < price_for_shop_for_day
                else "no_payment"
            )
        )
        return result

    except Exception as e:  # noqa: BLE001
        logger.error("Cabinet %s: необработанная ошибка: %s", cabinet_id, e)
        result["reason"] = f"unexpected_error:{e}"
        return result


@inject
async def process_payment_for_advs(
    redis_manager: RedisManager = Provide[BillingContainer.redis_manager],
    redis_lock: RedisLock = Provide[BillingContainer.redis_lock],
    global_ttl: int = 3600,  # увеличен TTL до 1 часа
) -> None:
    """Глобальная точка входа: один глобальный Redis-лок (без даты), без авто-продления.

    Порядок:
      1. acquire_lock()
      2. _process_payment_for_advs()
      3. release_lock()
    """
    current_dt = datetime.now()
    acquired = False
    pricer = Pricer()
    try:
        acquired = await redis_lock.acquire_lock(ttl=global_ttl)
        if not acquired:
            logger.info("Billing already running (global lock busy)")
            return None
        await _process_payment_for_advs(
            current_date_time=current_dt,
            pricer=pricer,
            redis_manager=redis_manager,
        )
    finally:
        if acquired:
            try:
                await redis_lock.release_lock()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to release global billing lock {exc}")
    return None


async def _process_payment_for_advs(
    current_date_time: datetime,
    pricer: Pricer,
    redis_manager: RedisManager,
    skip_by_redis: bool = True,
) -> None:
    """Внутренний цикл обработки всех кабинетов (без глобального лока).

    Отдельная функция нужна, чтобы глобальная обёртка могла ставить/снимать лок
    и при этом логика цикла была тестируемой изолированно.
    """
    current_dt = current_date_time
    async with sm(read_only=True) as preload_session:
        cabinet_ids = await _fetch_active_cabinet_ids(preload_session)

    if not cabinet_ids:
        logger.debug("Нет активных кабинетов с кампаниями (read-only выборка)")
        return
    logger.debug(f"К обработке кабинетов: {len(cabinet_ids)}")
    coros: list[Coroutine[Any, Any, CabinetProcessResult]] = []

    for cabinet_id in cabinet_ids:
        coros.append(
            _process_single_cabinet(
                cabinet_id=cabinet_id,
                current_dt=current_dt,
                pricer=pricer,
                redis_manager=redis_manager,
                skip_by_redis=skip_by_redis,
            )
        )
    results = await asyncio.gather(*coros, return_exceptions=True)
    for res in results:
        if isinstance(res, BaseException):
            logger.error("Ошибка в обработке кабинета: %s", res, exc_info=True)
        else:
            payload: CabinetProcessResult = res
            logger.info(
                "Cabinet %s: processed=%s, payment_successful=%s, reason=%s, campaigns=%s, price_for_day=%s",
                payload.get("cabinet_id"),
                payload.get("processed"),
                payload.get("payment_successful"),
                payload.get("reason"),
                payload.get("campaigns"),
                payload.get("price_for_day"),
            )
