INSERT INTO default_db.clusters_adv_deltas_5m
(adv_id,nmid,norm_query,ts5,dviews,dcarts,dclicks,dorders,pos_bin,cpm_mid,dspend_est,gap_minutes,is_reset,src_ts,version)
WITH
    toInt32({time_from_hours:Int32}) AS time_from_hours,
    6 AS overlap_hours,
    30 AS GAP_MAX_MINUTES,
    now() - toIntervalHour(time_from_hours) AS t_from,
    now() + INTERVAL 5 MINUTE AS t_to
SELECT
    adv_id,
    nmid,
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
            norm_query,
            toStartOfInterval(timestamp, INTERVAL 5 MINUTE) AS ts5,
            argMax(views, timestamp) AS views5,
            argMax(add_to_cart, timestamp) AS carts5,
            argMax(clicks, timestamp) AS clicks5,
            argMax(orders, timestamp) AS orders5,
            argMax(avr_pos, timestamp) AS pos5,
            argMax(cpm, timestamp) AS cpm5,
            max(timestamp) AS src_ts
        FROM default_db.clusters_adv_stats
        WHERE timestamp >= t_from - toIntervalHour(overlap_hours)
          AND timestamp <  t_to
          AND date >= toDate(t_from - toIntervalHour(overlap_hours))
          AND date <= toDate(t_to)
        GROUP BY adv_id,nmid,norm_query,ts5
    )
)
WHERE dviews > 0
  AND ts5 >= t_from
  AND ts5 <  t_to
