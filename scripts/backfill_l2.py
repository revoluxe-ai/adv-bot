from __future__ import annotations

import asyncio
from datetime import date, timedelta, datetime, timezone

from app.utils.click_house.client import get_clickhouse_client


# --------------------------------------------------
# диапазон дат в L1
# --------------------------------------------------
SELECT_MIN_MAX_DATE = """
SELECT
    toString(min(date)) AS date_from,
    toString(max(date)) AS date_to,
    count()             AS rows_cnt
FROM default_db.adv_state_snapshots
"""


# --------------------------------------------------
# проверка наличия состояний за день
# --------------------------------------------------
SELECT_COUNT_DAY = """
SELECT count()
FROM default_db.adv_state_snapshots
WHERE date = toDate(%(day)s)
"""


# --------------------------------------------------
# вставка L2 (TICKS) за один день
# --------------------------------------------------
INSERT_L2_TICKS_DAY = """
INSERT INTO default_db.adv_events_ticks
(
    adv_id,
    nmid,
    norm_query,
    date,
    ts,
    d_views,
    d_clicks,
    d_carts,
    d_orders,
    ver
)
SELECT
    adv_id,
    nmid,
    norm_query,
    date,
    ts,

    greatest(views  - prev_views,  0) AS d_views,
    greatest(clicks - prev_clicks, 0) AS d_clicks,
    greatest(carts  - prev_carts,  0) AS d_carts,
    greatest(orders - prev_orders, 0) AS d_orders,

    %(ver)s AS ver
FROM
(
    SELECT
        adv_id,
        nmid,
        norm_query,
        date,
        ts,
        views,
        clicks,
        carts,
        orders,

        lagInFrame(views)  OVER w AS prev_views,
        lagInFrame(clicks) OVER w AS prev_clicks,
        lagInFrame(carts)  OVER w AS prev_carts,
        lagInFrame(orders) OVER w AS prev_orders
    FROM default_db.adv_state_snapshots
    WHERE date = toDate(%(day)s)
    WINDOW w AS (
        PARTITION BY adv_id, nmid, norm_query
        ORDER BY ts
        ROWS BETWEEN 1 PRECEDING AND 1 PRECEDING
    )
)
SETTINGS
    max_threads = 1,
    max_insert_threads = 1
"""


async def backfill_l2_ticks_by_day() -> None:
    async with get_clickhouse_client() as client:
        res = await client.query(SELECT_MIN_MAX_DATE)
        date_from_s, date_to_s, rows_cnt = res.result_rows[0]

    if rows_cnt == 0 or not date_from_s:
        print("adv_state_snapshots is empty — nothing to backfill")
        return

    date_from = date.fromisoformat(date_from_s)
    date_to = date.fromisoformat(date_to_s)

    print(f"L2 ticks backfill range: {date_from} → {date_to}")

    async with get_clickhouse_client() as client:
        d = date_from
        while d <= date_to:
            res = await client.query(
                SELECT_COUNT_DAY,
                {"day": d.isoformat()},
            )
            cnt = res.result_rows[0][0]

            if cnt == 0:
                print(f"{d}: no states, skip")
                d += timedelta(days=1)
                continue

            # одна версия на весь день (идемпотентность)
            ver = int(datetime.now(timezone.utc).timestamp())

            print(f"{d}: states={cnt}, inserting ticks (ver={ver})")

            await client.query(
                INSERT_L2_TICKS_DAY,
                {
                    "day": d.isoformat(),
                    "ver": ver,
                },
            )

            print(f"{d}: done")
            d += timedelta(days=1)

    print("L2 ticks backfill completed")


if __name__ == "__main__":
    asyncio.run(backfill_l2_ticks_by_day())
