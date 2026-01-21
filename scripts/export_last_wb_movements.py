"""Script to export the most recent WB balance or bonus movement per cabinet."""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv  # isort: skip  # noqa: E402

from sqlalchemy import and_, case, func, literal, select, text, union_all

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBBalancePayment,
    WBBonusPayment,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker


dotenv.load_dotenv()


def build_latest_movement_stmt():
    """Return a select statement that yields the latest movement per WB cabinet."""
    balance_alias = select(
        WBBalancePayment.wb_cabinet_id.label("wb_cabinet_id"),
        literal("balance").label("source"),
        WBBalancePayment.amount.label("amount"),
        WBBalancePayment.description.label("description"),
        WBBalancePayment.transaction_date_time.label("transaction_date_time"),
        WBBalancePayment.operation_type.label("operation_type"),
    )

    bonus_alias = select(
        WBBonusPayment.wb_cabinet_id.label("wb_cabinet_id"),
        literal("bonus").label("source"),
        WBBonusPayment.amount.label("amount"),
        WBBonusPayment.description.label("description"),
        WBBonusPayment.transaction_date_time.label("transaction_date_time"),
        WBBonusPayment.operation_type.label("operation_type"),
    )

    combined = union_all(balance_alias, bonus_alias).subquery("combined_movements")

    spend_union = union_all(
        select(
            WBBalancePayment.wb_cabinet_id.label("wb_cabinet_id"),
            WBBalancePayment.amount.label("amount"),
            WBBalancePayment.transaction_date_time.label("transaction_date_time"),
        ),
        select(
            WBBonusPayment.wb_cabinet_id.label("wb_cabinet_id"),
            WBBonusPayment.amount.label("amount"),
            WBBonusPayment.transaction_date_time.label("transaction_date_time"),
        ),
    ).subquery("spend_movements")

    today = func.current_date()
    seven_days_ago = func.now() - text("INTERVAL '7 days'")

    spend_today = (
        select(
            spend_union.c.wb_cabinet_id,
            func.sum(func.abs(spend_union.c.amount)).label("spend_today"),
        )
        .where(
            and_(
                spend_union.c.amount < 0,
                func.date(spend_union.c.transaction_date_time) == today,
            )
        )
        .group_by(spend_union.c.wb_cabinet_id)
        .cte("spend_today")
    )

    spend_7d = (
        select(
            spend_union.c.wb_cabinet_id,
            func.sum(func.abs(spend_union.c.amount)).label("spend_7d"),
        )
        .where(
            and_(
                spend_union.c.amount < 0,
                spend_union.c.transaction_date_time >= seven_days_ago,
            )
        )
        .group_by(spend_union.c.wb_cabinet_id)
        .cte("spend_7d")
    )

    watchdog_counts = (
        select(
            AdvSetting.wb_cabinet_id.label("wb_cabinet_id"),
            func.count().label("watchdog_count"),
        )
        .where(
            and_(
                AdvSetting.auto_budget_watchdog_enabled.is_(True),
                AdvSetting.bot_active.is_(True),
            )
        )
        .group_by(AdvSetting.wb_cabinet_id)
        .cte("watchdog_counts")
    )

    movements = select(
        combined.c.wb_cabinet_id,
        combined.c.source,
        combined.c.amount,
        combined.c.description,
        combined.c.transaction_date_time,
        combined.c.operation_type,
        func.row_number()
        .over(
            partition_by=combined.c.wb_cabinet_id,
            order_by=combined.c.transaction_date_time.desc(),
        )
        .label("rn"),
    ).cte("latest_movements")

    balance_totals = (
        select(
            WBBalancePayment.wb_cabinet_id.label("wb_cabinet_id"),
            func.sum(WBBalancePayment.amount).label("balance_delta"),
        )
        .group_by(WBBalancePayment.wb_cabinet_id)
        .subquery("balance_totals")
    )

    bonus_totals = (
        select(
            WBBonusPayment.wb_cabinet_id.label("wb_cabinet_id"),
            func.sum(WBBonusPayment.amount).label("bonus_delta"),
        )
        .group_by(WBBonusPayment.wb_cabinet_id)
        .subquery("bonus_totals")
    )

    balance_total_expr = (
        func.coalesce(WBCabinet.balance, 0)
        + func.coalesce(balance_totals.c.balance_delta, 0)
    ).label("balance_total")

    bonus_total_expr = (
        func.coalesce(WBCabinet.bonus, 0)
        + func.coalesce(bonus_totals.c.bonus_delta, 0)
    ).label("bonus_total")

    remaining_total_expr = (
        balance_total_expr + bonus_total_expr
    ).label("remaining_total")

    avg_spend_base = func.coalesce(spend_7d.c.spend_7d, 0) / 7
    avg_spend_expr = avg_spend_base.label("avg_spend_7d")

    runway_expr = case(
        ((avg_spend_base == 0), None),
        else_=remaining_total_expr / func.nullif(avg_spend_base, 0),
    ).label("runway_days")

    stmt = (
            select(
            User.id.label("user_id"),
            User.username.label("username"),
            WBCabinet.shop_id.label("shop_id"),
            movements.c.wb_cabinet_id.label("wb_cabinet_id"),
            movements.c.source,
            movements.c.operation_type,
            movements.c.amount,
            movements.c.description,
            movements.c.transaction_date_time,
            balance_total_expr,
            bonus_total_expr,
            remaining_total_expr,
            func.coalesce(spend_today.c.spend_today, 0).label("spend_today"),
            avg_spend_expr,
            runway_expr,
                func.coalesce(watchdog_counts.c.watchdog_count, 0).label(
                    "watchdog_campaigns"
                ),
        )
        .select_from(movements)
        .join(
            WBCabinet,
            WBCabinet.id == movements.c.wb_cabinet_id,
        )
        .outerjoin(
            balance_totals,
            balance_totals.c.wb_cabinet_id == WBCabinet.id,
        )
        .outerjoin(
            bonus_totals,
            bonus_totals.c.wb_cabinet_id == WBCabinet.id,
        )
        .outerjoin(
            spend_today,
            spend_today.c.wb_cabinet_id == WBCabinet.id,
        )
        .outerjoin(
            spend_7d,
            spend_7d.c.wb_cabinet_id == WBCabinet.id,
        )
        .outerjoin(
            watchdog_counts,
            watchdog_counts.c.wb_cabinet_id == WBCabinet.id,
        )
        .join(
            WBUserCabinet,
            WBUserCabinet.wb_cabinet_id == WBCabinet.id,
        )
        .join(User, User.id == WBUserCabinet.user_id)
        .where(movements.c.rn == 1)
        .order_by(User.id, WBCabinet.shop_id)
    )

    return stmt


def direction_from_amount(amount: float | None) -> str:
    """Return human-readable type of operation."""
    if amount is None:
        return "списание"
    return "пополнение" if amount >= 0 else "списание"


def translate_source(source: str | None) -> str:
    """Translate the source literal to Russian."""
    if source == "bonus":
        return "бонус"
    return "баланс"


async def dump_movements_to_csv(output_path: Path) -> None:
    stmt = build_latest_movement_stmt()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with get_async_session_maker(read_only=True) as session:
        stream = await session.stream(stmt)  # type: ignore[attr-defined]
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "user_id",
                    "username",
                    "shop_id",
                    "источник",
                    "тип_операции",
                    "сумма",
                    "остаток_баланса",
                    "остаток_бонусов",
                    "remaining_total",
                    "spend_today",
                    "avg_spend_7d",
                    "runway_days",
                    "watchdog_campaigns",
                    "комментарий",
                    "время_последнего_движения",
                ]
            )

            index = 0
            async for row in stream:
                username = row.username or ""
                direction = direction_from_amount(row.amount)
                source = translate_source(row.source)
                balance_total = row.balance_total or 0.0
                bonus_total = row.bonus_total or 0.0
                remaining_total = row.remaining_total or 0.0
                spend_today = row.spend_today or 0.0
                avg_spend = row.avg_spend_7d or 0.0
                runway = row.runway_days
                watchdog_campaigns = row.watchdog_campaigns or 0
                writer.writerow(
                    [
                        row.user_id,
                        username,
                        row.shop_id,
                        source,
                        direction,
                        f"{row.amount:.2f}" if row.amount is not None else "",
                        f"{balance_total:.2f}",
                        f"{bonus_total:.2f}",
                        f"{remaining_total:.2f}",
                        f"{spend_today:.2f}",
                        f"{avg_spend:.2f}",
                        "" if runway is None else f"{runway:.2f}",
                        watchdog_campaigns,
                        row.description or "",
                        row.transaction_date_time.isoformat(),
                    ]
                )
                index += 1

            print(f"Exported {index} rows to {output_path}")


async def main(output_file: str):
    await dump_movements_to_csv(Path(output_file))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export latest WB balance/bonus movement per cabinet."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="export/last_wb_movements.csv",
        help="Path to CSV output.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.output))
