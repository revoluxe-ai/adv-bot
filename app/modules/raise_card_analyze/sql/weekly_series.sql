-- Weekly series: same residual, group by week. Base row filters.
WITH base AS (
    SELECT
        toMonday(toDate(decision_time)) AS week_start,
        toFloat64(greatest(0, views_curr - coalesce(views_prev, 0))) AS d_views,
        ln(least(greatest(pos_final, 1), {pos_cap:UInt32})) AS ln_pos,
        ln(least(greatest(final_bid, 1), {bid_cap:Float64})) AS ln_bid,
        norm_query
    FROM default_db.bid_decision_log
    WHERE adv_id = {adv_id:Int32}
      AND nmid = {nmid:UInt64}
      AND pos_final > 0
      AND final_bid > 0
      AND decision_time >= now() - toIntervalDay({series_days:UInt32})
),
filtered AS (
    SELECT
        week_start,
        ln_pos - {k_used:Float64} * ln_bid AS residual,
        toUInt64(greatest(1, d_views)) AS weight,
        d_views,
        norm_query
    FROM base
    WHERE d_views >= {min_d_views:UInt32}
)
SELECT
    week_start,
    quantileExactWeighted(0.5)(residual, weight) AS strength_index_med,
    sum(d_views) AS sum_d,
    sum(weight) AS sum_w,
    count() AS rows_filtered,
    uniq(norm_query) AS keys_filtered
FROM filtered
GROUP BY week_start
ORDER BY week_start
