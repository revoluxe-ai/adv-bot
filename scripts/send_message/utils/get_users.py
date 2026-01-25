from __future__ import annotations

import asyncio
import csv
import logging
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import Select, func, select, text, union_all, exists
from sqlalchemy.orm import aliased, selectinload

from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
    WBUserCabinet,
    WBCabinet,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

LOGGER = logging.getLogger(__name__)


def _build_recent_movement_user_ids(days: int) -> Select[tuple[int]]:
    """Return a statement yielding user IDs tied to recent WB movements."""
    if days <= 0:
        days = 1

    movement_union = union_all(
        select(
            WBBalancePayment.wb_cabinet_id.label("wb_cabinet_id"),
            WBBalancePayment.transaction_date_time.label("transaction_date_time"),
        ),
        select(
            WBBonusPayment.wb_cabinet_id.label("wb_cabinet_id"),
            WBBonusPayment.transaction_date_time.label("transaction_date_time"),
        ),
    ).subquery("movement_union")

    recent_bound = func.now() - text(f"INTERVAL '{days} days'")

    stmt: Select[tuple[int]] = (
        select(WBUserCabinet.user_id.label("user_id"))
        .select_from(
            movement_union.join(
                WBUserCabinet,
                WBUserCabinet.wb_cabinet_id == movement_union.c.wb_cabinet_id,
            )
        )
        .where(movement_union.c.transaction_date_time >= recent_bound)
        .distinct()
    )

    return stmt


def _cabinet_calculated_total(cabinet_alias: WBCabinet) -> Select:
    balance_payments_sum = (
        select(func.coalesce(func.sum(WBBalancePayment.amount), 0.0))
        .where(WBBalancePayment.wb_cabinet_id == cabinet_alias.id)
        .scalar_subquery()
    )
    bonus_payments_sum = (
        select(func.coalesce(func.sum(WBBonusPayment.amount), 0.0))
        .where(WBBonusPayment.wb_cabinet_id == cabinet_alias.id)
        .scalar_subquery()
    )
    return (
        cabinet_alias.balance
        + cabinet_alias.bonus
        + balance_payments_sum
        + bonus_payments_sum
    )


def _build_non_zero_balance_user_ids() -> Select[tuple[int]]:
    """Return a statement for users with cabinets whose totals != 0 but < 200, skipping users with any cabinet >= 200."""
    cabinet_total = _cabinet_calculated_total(WBCabinet)
    inner_cabinet = aliased(WBCabinet)
    inner_user_cabinet = aliased(WBUserCabinet)
    inner_total = _cabinet_calculated_total(inner_cabinet)

    large_balance_exists = exists(
        select(inner_user_cabinet.id)
        .join(inner_cabinet, inner_user_cabinet.wb_cabinet_id == inner_cabinet.id)
        .where(
            inner_user_cabinet.user_id == WBUserCabinet.user_id,
            inner_total >= 200,
        )
    )

    stmt: Select[tuple[int]] = (
        select(WBUserCabinet.user_id.label("user_id"))
        .join(WBCabinet, WBUserCabinet.wb_cabinet_id == WBCabinet.id)
        .where(
            cabinet_total != 0,
            cabinet_total < 200,
            ~large_balance_exists,
        )
        .distinct()
    )

    return stmt


async def _fetch_user_with_retries(user_id: int, retries: int = 3) -> User | None:
    backoff_delay = 0.1
    load_cabinet = (
        selectinload(User.wb_user_cabinets)
        .selectinload(WBUserCabinet.wb_cabinet)
    )

    stmt = (
        select(User)
        .options(
            load_cabinet.selectinload(WBCabinet.adv_settings),
            load_cabinet.selectinload(WBCabinet.balance_payments),
            load_cabinet.selectinload(WBCabinet.bonus_payments),
        )
        .where(User.id == user_id)
    )
    for attempt in range(1, retries + 1):
        try:
            async with get_async_session_maker(read_only=True) as user_session:
                result = await user_session.execute(stmt)
                user = result.scalar_one_or_none()
            return user
        except Exception:  # pragma: no cover - best-effort logging
            LOGGER.exception(
                "failed to load user %s on attempt %s/%s", user_id, attempt, retries
            )
            if attempt == retries:
                LOGGER.warning("giving up fetching user %s after %s attempts", user_id, retries)
            else:
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2
    return None


async def with_movements_for_last_days(days: int = 7) -> AsyncIterator[User]:
    """Yield fresh `User` ORM instances that had movements during the lookback."""
    stmt = _build_recent_movement_user_ids(days)
    async with get_async_session_maker(read_only=True) as session:
        result = await session.execute(stmt)
        user_ids = [row.user_id for row in result if row.user_id is not None]

    seen_ids: set[int] = set()
    for user_id in user_ids:
        if user_id in seen_ids:
            continue
        seen_ids.add(user_id)
        user = await _fetch_user_with_retries(user_id)
        if user is not None:
            yield user


async def with_non_zero_balance_users() -> AsyncIterator[User]:
    """Yield users who own at least one WB cabinet with a non-zero balance."""
    stmt = _build_non_zero_balance_user_ids()
    async with get_async_session_maker(read_only=True) as session:
        result = await session.execute(stmt)
        user_ids = [row.user_id for row in result if row.user_id is not None]

    seen_ids: set[int] = set()
    for user_id in user_ids:
        if user_id in seen_ids:
            continue
        seen_ids.add(user_id)
        user = await _fetch_user_with_retries(user_id)
        if user is not None:
            yield user


def _summarize_user_for_sales(user: User) -> list[dict[str, object]]:
    """Return a row per cabinet that the sales team cares about."""
    rows: list[dict[str, object]] = []

    for user_cabinet in user.wb_user_cabinets:
        cabinet = user_cabinet.wb_cabinet
        if cabinet is None:
            continue
        balance = float(cabinet.calculated_balance or 0)
        bonus = float(cabinet.calculated_bonus or 0)
        balance_plus_bonus = balance + bonus
        if balance_plus_bonus == 0 or balance_plus_bonus >= 200:
            continue
        active_campaigns = sum(
            1 for adv in getattr(cabinet, "adv_settings", []) or [] if adv.bot_active
        )
        rows.append(
            {
                "user_id": user.id,
                "telegram_id": user.user_telegram_id,
                "login": user.username or "",
                "cabinet_name": user_cabinet.name,
                "shop_id": cabinet.shop_id,
                "balance": balance,
                "bonus": bonus,
                "balance_plus_bonus": balance_plus_bonus,
                "active_campaigns": active_campaigns,
                "has_active_campaign": active_campaigns > 0,
            }
        )

    return rows


async def export_non_zero_balance_users_to_csv(
    dest_path: Path | str,
    *,
    limit: int | None = None,
) -> Path:
    """Write summarized rows for non-zero balance users into `dest_path`."""
    output = Path(dest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "user_id",
        "telegram_id",
        "login",
        "cabinet_name",
        "shop_id",
        "balance",
        "bonus",
        "balance_plus_bonus",
        "active_campaigns",
        "has_active_campaign",
    ]
    written = 0

    with output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        async for user in with_non_zero_balance_users():
            for row in _summarize_user_for_sales(user):
                writer.writerow(row)
                written += 1
                if limit is not None and written >= limit:
                    return output

    return output
