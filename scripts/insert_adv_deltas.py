# scripts/insert_adv_deltas.py
import argparse
import asyncio
import os
import sys
from datetime import datetime

# Add project root to sys.path
try:
    from set_path import add_project_root_to_path, get_project_path
except ImportError:
    from scripts.set_path import add_project_root_to_path, get_project_path

project_root = add_project_root_to_path()

import dotenv
dotenv.load_dotenv()

from app.utils.click_house.client import get_clickhouse_client
from clickhouse_connect.driver.asyncclient import AsyncClient

async def insert_adv_deltas(day_from_str: str, day_to_str: str):
    """
    Executes an INSERT INTO query for default_db.clusters_adv_deltas_5m for a specified date range.
    """
    query = f"""
INSERT INTO default_db.clusters_adv_deltas_5m
(
    adv_id,
    nmid,
    wb_category,
    norm_query,
    ts5,
    dviews,
    dcarts,
    dclicks,
    dorders,
    pos_bin,
    cpm_mid,
    dspend_est,
    gap_minutes,
    is_reset,
    src_ts,
    version
)
WITH
    toDateTime('{day_from_str} 00:00:00') AS day_from,
    toDateTime('{day_to_str} 00:00:00') AS day_to,
    6 AS OVERLAP_HOURS,
    30 AS GAP_MAX_MINUTES
SELECT
    adv_id,
    nmid,
    wb_category,
    norm_query,
    ts5,
    toUInt32(dviews) AS dviews,
    toUInt32(dcarts) AS dcarts,
    toUInt32(dclicks) AS dclicks,
    toUInt32(dorders) AS dorders,
    pos_bin,
    cpm_mid,
    toFloat32(dviews) * cpm_mid / 1000.0 AS dspend_est,
    gap_minutes,
    is_reset,
    src_ts,
    toUInt64(toUnixTimestamp(src_ts)) AS version
FROM
(
    SELECT
        adv_id,
        nmid,
        wb_category,
        norm_query,
        ts5,
        views5,
        carts5,
        clicks5,
        orders5,
        pos5,
        cpm5,
        src_ts,

        lagInFrame(views5)  OVER (PARTITION BY adv_id,nmid,norm_query ORDER BY ts5) AS prev_views5,
        lagInFrame(carts5)  OVER (PARTITION BY adv_id,nmid,norm_query ORDER BY ts5) AS prev_carts5,
        lagInFrame(clicks5) OVER (PARTITION BY adv_id,nmid,norm_query ORDER BY ts5) AS prev_clicks5,
        lagInFrame(orders5) OVER (PARTITION BY adv_id,nmid,norm_query ORDER BY ts5) AS prev_orders5,
        lagInFrame(cpm5)    OVER (PARTITION BY adv_id,nmid,norm_query ORDER BY ts5) AS prev_cpm5,
        lagInFrame(src_ts)  OVER (PARTITION BY adv_id,nmid,norm_query ORDER BY ts5) AS prev_ts,
        toUInt16(if(prev_ts IS NULL, 0, greatest(0, dateDiff('minute', prev_ts, src_ts)))) AS gap_minutes,

        toUInt8(
            (prev_views5  IS NOT NULL AND views5  < prev_views5) OR
            (prev_carts5  IS NOT NULL AND carts5  < prev_carts5) OR
            (prev_clicks5 IS NOT NULL AND clicks5 < prev_clicks5) OR
            (prev_orders5 IS NOT NULL AND orders5 < prev_orders5)
        ) AS is_reset,

        toUInt32(if(prev_views5  IS NULL OR is_reset=1 OR gap_minutes>GAP_MAX_MINUTES, 0, greatest(0, views5  - prev_views5 ))) AS dviews,
        toUInt32(if(prev_carts5  IS NULL OR is_reset=1 OR gap_minutes>GAP_MAX_MINUTES, 0, greatest(0, carts5  - prev_carts5 ))) AS dcarts,
        toUInt32(if(prev_clicks5 IS NULL OR is_reset=1 OR gap_minutes>GAP_MAX_MINUTES, 0, greatest(0, clicks5 - prev_clicks5))) AS dclicks,
        toUInt32(if(prev_orders5 IS NULL OR is_reset=1 OR gap_minutes>GAP_MAX_MINUTES, 0, greatest(0, orders5 - prev_orders5))) AS dorders,
        toUInt16(greatest(1, least(300, toUInt32(round(pos5))))) AS pos_bin,
        toFloat32(if(prev_cpm5 IS NULL, cpm5, (cpm5 + prev_cpm5) / 2.0)) AS cpm_mid
    FROM
    (
        SELECT
            adv_id,
            nmid,

            -- категория внутри 5-мин бакета (последняя по timestamp)
            if(
                argMax(wb_category, timestamp) = '' OR isNull(argMax(wb_category, timestamp)),
                'UNKNOWN',
                argMax(wb_category, timestamp)
            ) AS wb_category,

            norm_query,
            toStartOfInterval(timestamp, INTERVAL 5 MINUTE) AS ts5,

            argMax(views,       timestamp) AS views5,
            argMax(add_to_cart, timestamp) AS carts5,
            argMax(clicks,      timestamp) AS clicks5,
            argMax(orders,      timestamp) AS orders5,
            argMax(avr_pos,     timestamp) AS pos5,
            argMax(cpm,         timestamp) AS cpm5,

            max(timestamp) AS src_ts
        FROM default_db.clusters_adv_stats
        WHERE timestamp >= day_from - INTERVAL OVERLAP_HOURS HOUR
          AND timestamp <  day_to
          AND date >= toDate(day_from - INTERVAL OVERLAP_HOURS HOUR)
          AND date <  toDate(day_to)
        GROUP BY adv_id, nmid, norm_query, ts5
    )
)
WHERE dviews > 0
  AND ts5 >= day_from
  AND ts5 <  day_to;

    """

    try:
        async with get_clickhouse_client() as client:
            await client.command(query)
        print(f"Successfully inserted adv deltas from {day_from_str} to {day_to_str}.")
    except Exception as e:
        print(f"Error inserting adv deltas: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insert advertisement deltas into ClickHouse.")
    parser.add_argument("--day_from", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--day_to", type=str, required=True, help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Basic date format validation
    try:
        datetime.strptime(args.day_from, "%Y-%m-%d")
        datetime.strptime(args.day_to, "%Y-%m-%d")
    except ValueError:
        print("Error: Date format must be YYYY-MM-DD.")
        sys.exit(1)

    asyncio.run(insert_adv_deltas(args.day_from, args.day_to))
