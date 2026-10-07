-- ============================================================================
-- bid_decision_timeline.sql
-- ============================================================================
-- Назначение: all bid_decision_log rows ≤ cutoff for trusted adv_ids (timeline export).
-- Таблица(и): default_db.bid_decision_log
-- Параметры: adv_ids, package_cutoff_instant
-- Вызывается: ChBidDecisionReader.fetch_timeline
-- ============================================================================
SELECT
    adv_id,
    nmid,
    norm_query,
    cpm_curr,
    final_bid,
    decision_time,
    stats_max_timestamp,
    decision_source,
    version
FROM default_db.bid_decision_log
WHERE adv_id IN {adv_ids:Array(Int32)}
  AND decision_time <= {package_cutoff_instant:DateTime}
  AND (
      stats_max_timestamp IS NULL
      OR stats_max_timestamp <= {package_cutoff_instant:DateTime}
  )
ORDER BY adv_id, nmid, norm_query, decision_time, version
