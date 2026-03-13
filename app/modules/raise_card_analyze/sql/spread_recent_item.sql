-- Spread (p90/p10 bid_clip) for item on last 14 days, min_d_views=1. For spread_used_recent.
WITH base AS (
    SELECT
        toFloat64(greatest(0, views_curr - coalesce(views_prev, 0))) AS d_views,
        least(greatest(final_bid, 1), {bid_cap:Float64}) AS bid_clip
    FROM default_db.bid_decision_log
    WHERE adv_id = {adv_id:Int32}
      AND nmid = {nmid:UInt64}
      AND pos_final > 0
      AND final_bid > 0
      AND decision_time >= now() - toIntervalDay(14)
),
filtered AS (
    SELECT bid_clip FROM base WHERE d_views >= 1
)
SELECT
    count() AS rows_recent,
    if(count() >= {spread_min_rows:UInt32}, quantile(0.9)(bid_clip) / nullIf(quantile(0.1)(bid_clip), 0), NULL) AS spread
FROM filtered
