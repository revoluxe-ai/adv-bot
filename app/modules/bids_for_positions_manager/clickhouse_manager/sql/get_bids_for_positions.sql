WITH
   {nmid:UInt64} AS v_nmid,
    toDateTime(now(), 'Europe/Moscow') AS ts_now,
    ts_now - INTERVAL 365 DAY AS ts_from
SELECT
    norm_query,
    pos_final_bucket AS pos_bin,
    argMax(final_bid, version) AS bid_cpm,
    argMax(decision_time, version) AS last_decision_time,
    argMax(decision_source, version) AS last_decision_source,
    argMax(stats_max_timestamp, version) AS last_stats_ts
FROM default_db.bid_decision_log
WHERE nmid = v_nmid
  AND final_bid > 0
  AND decision_time >= ts_from
GROUP BY
    norm_query,
    pos_bin
ORDER BY
    norm_query,
    pos_bin
