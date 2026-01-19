from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any, Type

from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
    WBUserCabinet,
    WBCabinet,
)
from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm


SELECT_BATCH_SIZE = 20


def build_low_balance_stmt(after_id: int | None) -> Select[User]:
    stmt = (
        select(User)
        .where(User.wb_user_cabinets.any())
        .options(
            selectinload(User.wb_user_cabinets)
            .selectinload(WBUserCabinet.wb_cabinet)
        )
        .order_by(User.id)
    )
    if after_id is not None:
        stmt = stmt.where(User.id > after_id)
    return stmt.limit(SELECT_BATCH_SIZE)


async def get_users_with_low_balance_and_near_last_payment(
    max_balance: float,
    max_days_since_last_payment: int,
    min_days_since_last_payment: int,
) -> AsyncGenerator[User, None]:
    """Yield (user, last_payment) for low-balance users whose last top-up falls into [min_days, max_days]."""

    if min_days_since_last_payment > max_days_since_last_payment:
        raise ValueError(
            "min_days_since_last_payment must be less than or equal to max_days_since_last_payment"
        )

    now = datetime.now(UTC)
    max_age_threshold = now - timedelta(days=max_days_since_last_payment)
    latest_allowed = now - timedelta(days=min_days_since_last_payment)


    last_id: int | None = None
    max_balance_value = float(max_balance)
    while True:
        async with sm(read_only=True) as session:
            stmt = build_low_balance_stmt(last_id)
            result = await session.execute(stmt)
            users_batch = result.scalars().all()
            if not users_batch:
                break
        all_cabinet_ids = {
            cab.wb_cabinet_id
            for user in users_batch
            for cab in user.wb_user_cabinets
        }
        balance_map = await _fetch_last_payments(WBBalancePayment, all_cabinet_ids
        )
        bonus_map = await _fetch_last_payments( WBBonusPayment, all_cabinet_ids
        )

        for user in users_batch:
            should_include_user = False
            wb_user_cabinets = user.wb_user_cabinets
            cabinet_ids = [cab.wb_cabinet_id for cab in wb_user_cabinets]
            if not cabinet_ids:
                continue

            for wb_user_cabinet in wb_user_cabinets:
                wb_cabinet = wb_user_cabinet.wb_cabinet
                balance, bonus = await get_cabinet_balance(wb_cabinet.id)
                total_money = balance + bonus

                if total_money < max_balance_value:
                    should_include_user = True
                    break

            if not should_include_user:
                continue

            candidate_times = []
            for cab_id in cabinet_ids:
                balance_time = balance_map.get(cab_id)
                bonus_time = bonus_map.get(cab_id)
                if balance_time is not None:
                    candidate_times.append(_ensure_utc(balance_time))
                if bonus_time is not None:
                    candidate_times.append(_ensure_utc(bonus_time))
            last_payment = max(candidate_times, default=None)

            if last_payment and max_age_threshold <= last_payment <= latest_allowed:
                print(user.username )
                yield user

            last_id = users_batch[-1].id


async def _fetch_last_payments(
    model: Type[Any],
    cabinet_ids: set[int],
) -> dict[int, datetime]:
    if not cabinet_ids:
        return {}
    stmt = (
        select(
            model.wb_cabinet_id,
            func.max(model.transaction_date_time),
        )
        .where(
            model.wb_cabinet_id.in_(cabinet_ids),
            model.amount > 0,
        )
        .group_by(model.wb_cabinet_id)
    )
    async with sm(read_only=True) as session:
        result = await session.execute(stmt)
        return {row[0]: row[1] for row in result}


def _ensure_utc(value: datetime) -> datetime:
    """Normalize datetimes to UTC so comparisons are safe."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
