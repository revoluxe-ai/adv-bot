from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any, Type

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from scripts.send_message.utils.get_users_with_low_balance import (
    get_users_with_low_balance,
)


async def get_users_with_low_balance_and_near_last_payment(
    max_balance: float = 200,
    payments_days_ago: int = 120,
) -> AsyncGenerator[User, None]:
    """Yield users with low balance that received top-ups recently."""

    threshold = datetime.now(UTC) - timedelta(days=payments_days_ago)
    async with sm() as payment_session:
        async for user in get_users_with_low_balance(max_balance=max_balance):
            cabinet_ids = [cab.wb_cabinet_id for cab in user.wb_user_cabinets]
            if not cabinet_ids:
                continue

            if await _has_recent_topups(payment_session, cabinet_ids, threshold):
                yield user


async def _has_recent_topups(
    session: Any,
    cabinet_ids: list[int],
    threshold: datetime,
) -> bool:
    """Return True if any positive balance or bonus deposits exist."""

    return (
        await _has_recent_payment_of_type(
            session,
            WBBalancePayment,
            cabinet_ids,
            threshold,
        )
        or await _has_recent_payment_of_type(
            session,
            WBBonusPayment,
            cabinet_ids,
            threshold,
        )
    )


async def _has_recent_payment_of_type(
    session: Any,
    model: Type[Any],
    cabinet_ids: list[int],
    threshold: datetime,
) -> bool:
    stmt = (
        select(model.id)
        .where(
            model.wb_cabinet_id.in_(cabinet_ids),
            model.amount > 0,
            model.transaction_date_time >= threshold,
        )
        .limit(1)
    )
    return (await session.scalar(stmt)) is not None
