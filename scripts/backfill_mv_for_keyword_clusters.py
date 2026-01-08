from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.utils.click_house.client import get_clickhouse_client


# --------------------------------------------------
# диапазон дат в raw
# --------------------------------------------------
SELECT_MIN_MAX_DATE = """
SELECT
    toString(min(date)) AS date_from,
    toString(max(date)) AS date_to,
    count()             AS rows_cnt
FROM default_db.clusters_adv_stats
"""


# --------------------------------------------------
# проверка наличия данных за день
# --------------------------------------------------
SELECT_COUNT_DAY = """
SELECT count()
FROM default_db.clusters_adv_stats
WHERE date = toDate(%(day)s)
"""


# --------------------------------------------------
# вставка L1 за один день
# --------------------------------------------------
INSERT_L1_DAY = """
INSERT INTO default_db.adv_state_snapshots
(
    adv_id,
    nmid,
    norm_query,
    date,
    views,
    clicks,
    carts,
    orders,
    ts,
    ver
)
SELECT
    adv_id,
    nmid,
    toLowCardinality(norm_query) AS norm_query,
    date,
    views,
    clicks,
    add_to_cart AS carts,
    orders,
    timestamp AS ts,
    (18446744073709551615 - toUInt64(toUnixTimestamp(timestamp))) AS ver
FROM default_db.clusters_adv_stats
WHERE date = toDate(%(day)s)
SETTINGS
    max_threads = 1,
    max_insert_threads = 1
"""


async def backfill_l1_by_day() -> None:
    async with get_clickhouse_client() as client:
        res = await client.query(SELECT_MIN_MAX_DATE)
        date_from_s, date_to_s, rows_cnt = res.result_rows[0]

    if rows_cnt == 0 or not date_from_s:
        print("clusters_adv_stats is empty — nothing to backfill")
        return

    date_from = date.fromisoformat(date_from_s)
    date_to = date.fromisoformat(date_to_s)

    print(f"L1 backfill range: {date_from} → {date_to}")

    async with get_clickhouse_client() as client:
        d = date_from
        while d <= date_to:
            res = await client.query(
                SELECT_COUNT_DAY,
                {"day": d.isoformat()},
            )
            cnt = res.result_rows[0][0]

            if cnt == 0:
                print(f"{d}: no data, skip")
                d += timedelta(days=1)
                continue

            print(f"{d}: raw rows={cnt}, inserting into L1…")

            await client.query(
                INSERT_L1_DAY,
                {"day": d.isoformat()},
            )

            print(f"{d}: done")

            d += timedelta(days=1)

    print("L1 backfill completed")


if __name__ == "__main__":
    asyncio.run(backfill_l1_by_day())
