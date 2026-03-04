-- Aggregates (norm_query, day) for corr: median bid_clip, median pos_clip, sum(d_views). Filter sum_d >= CORR_MIN_SUM_D.
-- min_d_views not used for corr. Used to compute weighted corr in Python; if points < CORR_MIN_POINTS then corr_ln=None.
WITH base AS (
    SELECT
        norm_query,
        toDate(decision_time) AS day,
        toFloat64(greatest(0, views_curr - coalesce(views_prev, 0))) AS d_views,
        least(greatest(pos_final, 1), {pos_cap:UInt32}) AS pos_clip,
        least(greatest(final_bid, 1), {bid_cap:Float64}) AS bid_clip
    FROM default_db.bid_decision_log
    WHERE adv_id = {adv_id:Int32}
      AND nmid = {nmid:UInt64}
      AND pos_final > 0
      AND final_bid > 0
      AND decision_time >= now() - toIntervalDay({window_days:UInt32})
),
agg AS (
    SELECT
        norm_query,
        day,
        median(pos_clip) AS pos_median,
        median(bid_clip) AS bid_median,
        sum(d_views) AS sum_d
    FROM base
    GROUP BY norm_query, day
)
SELECT
    norm_query,
    day,
    pos_median,
    bid_median,
    sum_d
FROM agg
WHERE sum_d >= {corr_min_sum_d:Float64}
ORDER BY norm_query, day
