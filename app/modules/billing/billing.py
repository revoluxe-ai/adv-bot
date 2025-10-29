"""Billing per-cabinet daily charges with Redis/DB dedup and Redis locks (без pg_advisory_lock)."""

import asyncio
import logging
from datetime import datetime, timedelta

from dependency_injector.wiring import inject, Provide
from sqlalchemy import exists, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.billing.di import BillingContainer
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting, WBBalancePayment, WBBonusPayment, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm
from .models import AdvPayment
from .redis_lock import RedisLock
from .redis_manager import RedisManager

logger = logging.getLogger(__name__)


async def _fetch_active_cabinet_ids(session: AsyncSession) -> list[int]:
    """Вернуть id кабинетов, у которых есть активные кампании.
    Используем только id чтобы потом загружать свежие данные в отдельных коротких транзакциях.
    """
    stmt = (
        select(WBCabinet.id)
        .where(exists(select(1).where(AdvSetting.wb_cabinet_id == WBCabinet.id, AdvSetting.bot_active)))
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def _load_cabinet_with_relations(session: AsyncSession, cabinet_id: int) -> WBCabinet | None:
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


async def _safe_commit(session: AsyncSession, result: dict[str, int | bool | str | float | None],
                       cabinet_id: int) -> bool:
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
) -> dict[str, int | bool | str | float | None]:
    async with sm() as session:
        return await __process_single_cabinet(
            session=session,
            cabinet_id=cabinet_id,
            current_dt=current_dt,
            pricer=pricer,
            redis_manager=redis_manager,
        )



async def __process_single_cabinet(
        session: AsyncSession,
        cabinet_id: int,
        current_dt: datetime,
        pricer: Pricer,
        redis_manager: RedisManager,
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
    Порядок операций: проверка Redis -> лок -> транзакция БД -> commit -> Redis-флаг.
    Redis-флаг – ускоритель, а не источник истины: при его сбое повтор безопасен.
    """
    result: dict[str, int | bool | str | float | None] = {
        "cabinet_id": cabinet_id,
        "processed": False,
        "payment_successful": False,
        "reason": "",
        "campaigns": 0,
        "price_for_day": None,
    }

    # # Быстрая проверка идемпотентности по Redis
    if await redis_manager.get_billing_process_for_day(cabinet_id, current_dt):
        result["reason"] = "redis_flag_skip"
        return result

    try:
        wb_cabinet = await _load_cabinet_with_relations(session, cabinet_id)
        if wb_cabinet is None:
            result["reason"] = "cabinet_not_found"
            await session.rollback()
            return result

        cabinet_campaigns: list[AdvSetting] = [adv for adv in wb_cabinet.adv_settings if adv.bot_active]
        result["campaigns"] = len(cabinet_campaigns)
        if not cabinet_campaigns:
            # Помечаем, чтобы не гонять лишний раз сегодня
            await session.commit()
            try:
                await redis_manager.set_billing_process_for_day(cabinet_id, current_dt)
            except Exception as exc:
                logger.error(f'Ошибка отметки в Redis: {exc}')  # noqa: BLE001
                pass
            result["reason"] = "no_active_campaigns"
            return result

        day = current_dt.date()
        day_start = datetime.combine(day, datetime.min.time())
        next_day = day_start + timedelta(days=1)

        # Проверка уже существующих списаний
        bonus_count = (
                          await session.scalar(
                              select(func.count(WBBonusPayment.id)).where(and_(
                                  WBBonusPayment.wb_cabinet_id == cabinet_id,
                                  WBBonusPayment.transaction_date_time >= day_start,
                                  WBBonusPayment.transaction_date_time < next_day,
                                  WBBonusPayment.operation_type == "auto_subtract",
                                  WBBonusPayment.amount < 0,
                              ))
                          )
                      ) or 0
        balance_count = (
                            await session.scalar(
                                select(func.count(WBBalancePayment.id)).where(and_(
                                    WBBalancePayment.wb_cabinet_id == cabinet_id,
                                    WBBalancePayment.transaction_date_time >= day_start,
                                    WBBalancePayment.transaction_date_time < next_day,
                                    WBBalancePayment.operation_type == "auto_subtract",
                                    WBBalancePayment.amount < 0,
                                ))
                            )
                        ) or 0
        if bonus_count > 0 or balance_count > 0:
            await session.commit()
            try:
                await redis_manager.set_billing_process_for_day(cabinet_id, current_dt)
            except Exception as exc:
                logger.error(f'Ошибка устанвоки значения в Redis {exc}')  # noqa: BLE001
                pass
            result["reason"] = "already_processed_db"
            return result

        try:
            price_for_shop_for_day = await pricer.get_price_for_day_for_shop(session, wb_cabinet.shop_id)
        except Exception as exc:
            logger.error('Cabinet %s: ошибка получения цены: %s', cabinet_id, exc, exc_info=True)
            raise exc

        result["price_for_day"] = price_for_shop_for_day
        if price_for_shop_for_day <= 0:
            try:
                await redis_manager.set_billing_process_for_day(cabinet_id, current_dt)
            except Exception as exc:
                logger.warning('Cabinet %s: zero price but Redis-флаг не установлен: %s', cabinet_id, exc)
                pass
            result["reason"] = "zero_price"
            return result

        calculated_bonus = float(wb_cabinet.calculated_bonus or 0) # type: ignore[truthy-function]
        calculated_balance = float(wb_cabinet.calculated_balance or 0) # type: ignore[truthy-function]
        payment_successful = False

        def add_bonus(amt: float) -> None:
            session.add(
                WBBonusPayment(
                    amount=-amt,
                    description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {day}",
                    operation_type="auto_subtract",
                    transaction_date_time=datetime.now(),
                    wb_cabinet=wb_cabinet,
                )
            )

        def add_balance(amt: float) -> None:
            session.add(
                WBBalancePayment(
                    amount=-amt,
                    description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {day}",
                    operation_type="auto_subtract",
                    transaction_date_time=datetime.now(),
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
            # Недостаточно средств — деактивируем кампании
            for campaign in wb_cabinet.adv_settings:
                if campaign.bot_active:
                    campaign.bot_active = False
                    campaign.auto_update_white_list = False
                    campaign.auto_update_target_place = False

        if payment_successful:
            price_per_campaign = price_for_shop_for_day / len(cabinet_campaigns)
            for campaign in cabinet_campaigns:
                exists_payment = await session.scalar(
                    select(func.count()).where(and_(
                        AdvPayment.adv_setting_id == campaign.id,
                        AdvPayment.date == day,
                    ))
                )
                if not exists_payment:
                    session.add(
                        AdvPayment(
                            date=day,
                            adv_setting_id=campaign.id,
                            amount=price_per_campaign,
                        )
                    )

        # Фиксация БД (укороченный helper)
        if not await _safe_commit(session, result, cabinet_id):
            return result

        # Флаг в Redis (best-effort)
        try:
            await redis_manager.set_billing_process_for_day(cabinet_id, current_dt)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Cabinet %s: commit успешен, но Redis-флаг не установлен (повтор допустим)",
                cabinet_id,
            )

        result["processed"] = True
        result["payment_successful"] = payment_successful
        result[
            "reason"] = "success" \
            if payment_successful else "deactivated" if not payment_successful \
                                                        and calculated_bonus + calculated_balance \
                                                        < price_for_shop_for_day else "no_payment"
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
    tasks_list = []

    for cabinet_id in cabinet_ids:
        task = _process_single_cabinet(
            cabinet_id=cabinet_id,
            current_dt=current_dt,
            pricer=pricer,
            redis_manager=redis_manager,
        )
        tasks_list.append(task)
    results = await asyncio.gather(*tasks_list, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            logger.error("Ошибка в обработке кабинета: %s", res, exc_info=True)
        elif isinstance(res, dict):
            logger.info(
                "Cabinet %s: processed=%s, payment_successful=%s, reason=%s, campaigns=%s, price_for_day=%s",
                res.get("cabinet_id"),
                res.get("processed"),
                res.get("payment_successful"),
                res.get("reason"),
                res.get("campaigns"),
                res.get("price_for_day"),
            )
        else:
            logger.error("Неожиданный результат обработки кабинета: %s", res)
