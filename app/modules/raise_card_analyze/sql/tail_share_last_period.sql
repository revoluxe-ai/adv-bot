-- tail_share and median pos on last period (last 7 days for cold, last 7 days for "last week"). Used for tail_mode.
-- Returns: tail_share (share of rows with pos_final > POS_CAP), median_pos, rows_count.
WITH base AS (
    SELECT
        pos_final,
        toFloat64(greatest(0, views_curr - coalesce(views_prev, 0))) AS d_views
    FROM default_db.bid_decision_log
    WHERE adv_id = {adv_id:Int32}
      AND nmid = {nmid:UInt64}
      AND pos_final > 0
      AND final_bid > 0
      AND decision_time >= now() - toIntervalDay({last_days:UInt32})
),
filtered AS (
    SELECT pos_final FROM base WHERE d_views >= {min_d_views:UInt32}
)
SELECT
    count() AS rows_count,
    countIf(pos_final > {pos_cap:Float64}) / nullIf(count(), 0) AS tail_share,
    quantile(0.5)(pos_final) AS median_pos
FROM filtered
