"""Test-only helpers: seed ``full_adv_wb_stat`` rows for leg-CPO CH integration seams.

Используется destructive-local integration tests для spec leg-cpo-economics.
Production SQL остаётся с ``default_db.*``; ``patch_get_clickhouse_client`` +
``RewritingClickHouseClient`` перенаправляют запросы в ``test_adv_bot_clickhouse``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clickhouse_connect import get_async_client

FULL_ADV_WB_STAT_COLUMNS = [
    "adv_id",
    "date",
    "views",
    "clicks",
    "spend",
    "added_to_cart",
    "orders",
    "sum_price_orders",
    "version",
]

LEG_CPO_FIXED_NOW = datetime(2026, 9, 29, 12, 0, 0)
LEG_CPO_FIXED_DAYS = 2
LEG_CPO_AUTO_ADV_ID = 9101
LEG_CPO_SEARCH_ADV_ID = 9202


def resolve_leg_cpo_window(
    *,
    now: datetime | None = None,
    days: int = LEG_CPO_FIXED_DAYS,
) -> tuple[datetime, datetime]:
    """Разрешить inclusive calendar-day окно так же, как ``leg_cpo.resolve_leg_cpo_window``."""
    anchor = now or datetime.now()
    return anchor - timedelta(days=days - 1), anchor


def leg_cpo_seed_dates(
    *,
    now: datetime | None = None,
    days: int = LEG_CPO_FIXED_DAYS,
) -> tuple[date, ...]:
    """Календарные даты окна для insert в ``full_adv_wb_stat``."""
    start, end = resolve_leg_cpo_window(now=now, days=days)
    dates: list[date] = []
    cursor = start.date()
    while cursor <= end.date():
        dates.append(cursor)
        cursor += timedelta(days=1)
    return tuple(dates)


async def truncate_full_adv_wb_stat(clickhouse_client: get_async_client) -> None:
    """Очистить test CH таблицу перед leg-CPO Arrange."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.full_adv_wb_stat"
    )


async def seed_leg_cpo_pair_rows(
    clickhouse_client: get_async_client,
    *,
    auto_adv_id: int = LEG_CPO_AUTO_ADV_ID,
    search_adv_id: int | None = LEG_CPO_SEARCH_ADV_ID,
    now: datetime | None = LEG_CPO_FIXED_NOW,
    days: int = LEG_CPO_FIXED_DAYS,
) -> tuple[datetime, datetime]:
    """Засидить Auto/Search ноги с раздельным spend/orders за observation window.

    Returns:
        ``(start_date, end_date)`` inclusive window, совпадающий с production loader.
    """
    start_date, end_date = resolve_leg_cpo_window(now=now, days=days)
    window_dates = leg_cpo_seed_dates(now=now, days=days)
    rows: list[tuple[int, date, int, int, float, int, int, float, float]] = []
    auto_spend_per_day = (600.0 / len(window_dates)) if window_dates else 600.0
    search_spend_per_day = (300.0 / len(window_dates)) if window_dates else 300.0
    auto_orders_total = 2
    search_orders_total = 3
    auto_orders_per_day = max(auto_orders_total // len(window_dates), 1)
    search_orders_per_day = max(search_orders_total // len(window_dates), 1)

    for day in window_dates:
        rows.append(
            (
                auto_adv_id,
                day,
                100,
                10,
                auto_spend_per_day,
                2,
                auto_orders_per_day,
                1000.0,
                1.0,
            )
        )
        if search_adv_id is not None:
            rows.append(
                (
                    search_adv_id,
                    day,
                    80,
                    8,
                    search_spend_per_day,
                    2,
                    search_orders_per_day,
                    800.0,
                    1.0,
                )
            )

    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.full_adv_wb_stat",
        rows,
        column_names=FULL_ADV_WB_STAT_COLUMNS,
    )
    return start_date, end_date


async def reread_leg_spend_totals(
    clickhouse_client: get_async_client,
    adv_ids: list[int],
    *,
    start_date: datetime,
    end_date: datetime,
) -> dict[int, tuple[float, int]]:
    """Re-read persisted spend/orders per adv_id from test CH (integration assert)."""
    result = await clickhouse_client.query(
        """
        SELECT
            adv_id,
            sum(spend) AS total_spend,
            sum(orders) AS total_orders
        FROM test_adv_bot_clickhouse.full_adv_wb_stat
        WHERE adv_id IN {adv_ids:Array(Int64)}
          AND date BETWEEN toDate({start_date:String}) AND toDate({end_date:String})
        GROUP BY adv_id
        ORDER BY adv_id
        """,
        parameters={
            "adv_ids": adv_ids,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        },
    )
    return {
        int(row[0]): (float(row[1] or 0.0), int(row[2] or 0))
        for row in result.result_rows
    }
