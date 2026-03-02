-- Buckets: group by week + round(bid_clip, -2). Base row filters. For Python to pick by max(sum_d).
WITH base AS (
    SELECT
        toMonday(toDate(decision_time)) AS week_start,
        toFloat64(greatest(0, views_curr - coalesce(views_prev, 0))) AS d_views,
        least(greatest(pos_final, 1), {pos_cap:UInt32}) AS pos_clip,
        least(greatest(final_bid, 1), {bid_cap:Float64}) AS bid_clip,
        round(least(greatest(final_bid, 1), {bid_cap:Float64}), -2) AS bid_bucket
    FROM default_db.bid_decision_log
    WHERE adv_id = {adv_id:Int32}
      AND nmid = {nmid:UInt64}
      AND pos_final > 0
      AND final_bid > 0
      AND decision_time >= now() - toIntervalDay(56)
),
filtered AS (
    SELECT week_start, bid_bucket, pos_clip, d_views, greatest(1, d_views) AS w
    FROM base
    WHERE d_views >= {min_d_views:UInt32}
)
SELECT
    week_start,
    bid_bucket,
    avg(pos_clip) AS avg_pos,
    count() AS rows,
    sum(d_views) AS sum_d,
    sum(w) AS sum_w
FROM filtered
GROUP BY week_start, bid_bucket
ORDER BY week_start, sum_d DESC
