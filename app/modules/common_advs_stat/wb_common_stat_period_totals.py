"""Агрегаты по `wb_common_stat` за скользящее окно в днях по списку nmids."""

from __future__ import annotations

_NMID_CHUNK = 4000

_SUM_LAST_DAYS_SQL = """
SELECT
    ifNull(sum(orders_sum), 0) AS orders_sum_rub,
    ifNull(sum(buyouts_sum_rub), 0) AS buyouts_sum_rub
FROM (
    SELECT
        nmid,
        date,
        argMax(orders_sum, version) AS orders_sum,
        argMax(buyouts_sum_rub, version) AS buyouts_sum_rub
    FROM default_db.wb_common_stat
    WHERE nmid IN {nmids:Array(UInt64)}
      AND date >= today() - {pass_days:UInt32}
    GROUP BY nmid, date
)
"""


async def sum_orders_and_buyouts_last_days_rub(
    nmids: list[int], *, pass_days: int = 30
) -> tuple[float, float]:
    """
    Сумма заказов и сумма выкупов (руб.) за последние `pass_days` календарных дней
    по дневным строкам с дедупликацией версии ReplacingMergeTree.
    """
    if pass_days < 1:
        raise ValueError("pass_days must be >= 1")
    unique: list[int] = []
    seen: set[int] = set()
    for raw in nmids:
        try:
            n = int(raw)
        except (TypeError, ValueError):
            continue
        if n not in seen:
            seen.add(n)
            unique.append(n)
    if not unique:
        return (0.0, 0.0)

    from app.utils.ch_semaphore import anti_ch_crash_semaphore
    from app.utils.click_house.client import get_clickhouse_client

    orders_total = 0.0
    buyouts_total = 0.0

    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            for i in range(0, len(unique), _NMID_CHUNK):
                chunk = unique[i : i + _NMID_CHUNK]
                result = await client.query(
                    _SUM_LAST_DAYS_SQL,
                    parameters={"nmids": chunk, "pass_days": pass_days},
                )
                if not result.result_rows:
                    continue
                row = result.result_rows[0]
                orders_total += float(row[0])
                buyouts_total += float(row[1])

    return (orders_total, buyouts_total)
