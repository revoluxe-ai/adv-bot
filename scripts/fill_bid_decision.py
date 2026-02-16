#!/usr/bin/env python3
import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


DT_FMT = "%Y-%m-%d %H:%M:%S"


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s, DT_FMT)


def fmt_dt(dt: datetime) -> str:
    return dt.strftime(DT_FMT)


def to_tz(dt: datetime, tz: str) -> datetime:
    tzinfo = ZoneInfo(tz)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tzinfo)
    return dt.astimezone(tzinfo)


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


GET_MINMAX_SQL = (
    "SELECT min(timestamp) AS ts_min, max(timestamp) AS ts_max "
    "FROM default_db.clusters_adv_stats"
)


def build_insert_sql(from_ts: str, to_ts: str, tz: str) -> str:
    from_ts = esc(from_ts)
    to_ts = esc(to_ts)
    tz = esc(tz)

    per_key_limit = 288

    return f"""
INSERT INTO default_db.bid_decision_log
(
    adv_id,
    nmid,
    norm_query,
    wb_category,
    pos_final,
    pos_final_bucket,
    views_curr,
    spend_curr,
    cpm_curr,
    pos_curr,
    views_prev,
    spend_prev,
    cpm_prev,
    pos_prev,
    final_bid,
    decision_source,
    stats_max_timestamp,
    decision_time,
    version
)
WITH
    toDateTime('{to_ts}', '{tz}') AS to_ts,
    toDateTime64(to_ts, 3, '{tz}') AS to_ts64,
    toDate(to_ts, '{tz}') AS target_date,
    toUInt64(toUnixTimestamp64Milli(to_ts64)) AS v
, changed_keys AS
(
    SELECT
        adv_id,
        nmid,
        norm_query
    FROM default_db.clusters_adv_stats
    WHERE
        timestamp >= toDateTime('{from_ts}', '{tz}')
        AND timestamp <  toDateTime('{to_ts}', '{tz}')
        AND (
            (spend IS NOT NULL)
            OR (cpm IS NOT NULL AND cpm > 0)
        )
        AND avr_pos > 0
    GROUP BY adv_id, nmid, norm_query
)
, recent AS
(
    SELECT
        s.adv_id,
        s.nmid,
        s.norm_query,
        s.wb_category,
        s.timestamp,
        s.views,
        s.spend,
        s.cpm,
        s.avr_pos
    FROM default_db.clusters_adv_stats AS s
    INNER JOIN changed_keys AS k USING (adv_id, nmid, norm_query)
    WHERE
        s.date = target_date
        AND s.timestamp < to_ts
        AND (
            (s.spend IS NOT NULL)
            OR (s.cpm IS NOT NULL AND s.cpm > 0)
        )
        AND s.avr_pos > 0
    ORDER BY s.timestamp DESC
    LIMIT {per_key_limit} BY s.adv_id, s.nmid, s.norm_query
)
, packed AS
(
    SELECT
        adv_id,
        nmid,
        norm_query,
        any(wb_category) AS wb_category,
        groupArray((timestamp, views, spend, cpm, avr_pos)) AS arr
    FROM recent
    GROUP BY adv_id, nmid, norm_query
)
SELECT
    adv_id,
    nmid,
    norm_query,
    wb_category,
    curr_pos AS pos_final,
    toUInt16(greatest(1, least(300, toUInt32(ceil(curr_pos))))) AS pos_final_bucket,
    curr_views AS views_curr,
    curr_spend AS spend_curr,
    curr_cpm AS cpm_curr,
    curr_pos AS pos_curr,
    prev_views AS views_prev,
    prev_spend AS spend_prev,
    prev_cpm AS cpm_prev,
    prev_pos AS pos_prev,
    if(ok_spend, effective_cpm, curr_cpm) AS final_bid,
    if(ok_spend, 'spend', 'cpm') AS decision_source,
    curr_ts AS stats_max_timestamp,
    to_ts AS decision_time,
    v AS version
FROM
(
    SELECT
        adv_id,
        nmid,
        norm_query,
        wb_category,
        (arr[1]).1 AS curr_ts,
        (arr[1]).2 AS curr_views,
        (arr[1]).3 AS curr_spend,
        (arr[1]).4 AS curr_cpm,
        (arr[1]).5 AS curr_pos,

        arrayFirst(x -> x.2 < curr_views, arr).2 AS prev_views,
        arrayFirst(x -> x.2 < curr_views, arr).3 AS prev_spend,
        arrayFirst(x -> x.2 < curr_views, arr).4 AS prev_cpm,
        arrayFirst(x -> x.2 < curr_views, arr).5 AS prev_pos,

        (prev_views IS NOT NULL)
            AND (curr_spend IS NOT NULL) AND (prev_spend IS NOT NULL)
            AND (curr_views - prev_views > 0)
            AND (toFloat64(curr_spend) - toFloat64(prev_spend) >= 0) AS ok_spend,

        if(
            (prev_views IS NOT NULL)
                AND (curr_spend IS NOT NULL) AND (prev_spend IS NOT NULL)
                AND (curr_views - prev_views > 0)
                AND (toFloat64(curr_spend) - toFloat64(prev_spend) >= 0),
            1000.0 * (toFloat64(curr_spend) - toFloat64(prev_spend))
                / nullIf(toFloat64(curr_views - prev_views), 0),
            NULL
        ) AS effective_cpm
    FROM packed
)
WHERE
    (curr_pos IS NOT NULL AND curr_pos > 0)
    AND (
        ok_spend
        OR (curr_cpm IS NOT NULL AND curr_cpm > 0)
    )
""".strip()




async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_ts")
    ap.add_argument("--to", dest="to_ts")
    ap.add_argument("--step-minutes", type=int, default=60)
    ap.add_argument("--tz", default="Europe/Moscow")
    ap.add_argument("--sleep-ms", type=int, default=0)
    args = ap.parse_args()

    from app.utils.click_house.client import get_clickhouse_client as get_client

    async with get_client() as client:
        # необязательно, но полезно для консистентности интерпретации дат/now()
        try:
            await client.query("SET session_timezone = 'Europe/Moscow'")
        except Exception:
            pass

        if args.from_ts and args.to_ts:
            start = parse_dt(args.from_ts)
            end = parse_dt(args.to_ts)
        else:
            res = await client.query(GET_MINMAX_SQL)
            start, end = res.first_row
            if not start or not end:
                print("Нет данных в clusters_adv_stats", file=sys.stderr)
                return 1

        if start >= end:
            print("Некорректный диапазон", file=sys.stderr)
            return 1

        start = to_tz(start, args.tz)
        end = to_tz(end, args.tz)

        step = timedelta(minutes=args.step_minutes)
        cur = start
        batch_no = 0

        print(f"Range: {start} .. {end}, step={args.step_minutes}m, tz={args.tz}")

        while cur < end:
            nxt = min(cur + step, end)
            batch_no += 1

            from_s = fmt_dt(cur)
            to_s = fmt_dt(nxt)

            print(f"[{batch_no}] {from_s} -> {to_s}", flush=True)

            sql = build_insert_sql(from_s, to_s, args.tz)
            await client.query(sql)

            if args.sleep_ms:
                await asyncio.sleep(args.sleep_ms / 1000)

            cur = nxt

        print(f"Done. batches={batch_no}")
        return 0


if __name__ == "__main__":
    asyncio.run(main())
