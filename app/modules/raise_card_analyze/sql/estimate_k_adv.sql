-- k regression for adv (adv_id, all nmid). Same base row filters.
WITH base AS (
    SELECT
        toFloat64(greatest(0, views_curr - coalesce(views_prev, 0))) AS d_views,
        least(greatest(pos_final, 1), {pos_cap:UInt32}) AS pos_clip,
        least(greatest(final_bid, 1), {bid_cap:Float64}) AS bid_clip,
        norm_query,
        decision_time
    FROM default_db.bid_decision_log
    WHERE adv_id = {adv_id:Int32}
      AND pos_final > 0
      AND final_bid > 0
      AND decision_time >= now() - toIntervalDay({window_days:UInt32})
),
filtered AS (
    SELECT ln(pos_clip) AS ln_pos, ln(bid_clip) AS ln_bid, greatest(1, d_views) AS weight, norm_query
    FROM base
    WHERE d_views >= {min_d_views:UInt32}
)
SELECT
    simpleLinearRegression(ln_bid, ln_pos).2 AS k,
    simpleLinearRegression(ln_bid, ln_pos).1 AS b,
    corr(ln_bid, ln_pos) AS corr_ln,
    count() AS rows_used,
    uniq(norm_query) AS keys_used,
    if(count() >= {spread_min_rows:UInt32}, quantile(0.9)(exp(ln_bid)) / nullIf(quantile(0.1)(exp(ln_bid)), 0), NULL) AS spread_ok
FROM filtered
