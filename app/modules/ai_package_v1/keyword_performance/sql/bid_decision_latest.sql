-- ============================================================================
-- bid_decision_latest.sql
-- ============================================================================
-- Назначение: row-coherent latest bid_decision_log per (adv_id, nmid, norm_query) ≤ cutoff.
-- Таблица(и): default_db.bid_decision_log
-- Параметры: adv_ids, package_cutoff_instant
-- Вызывается: ChBidDecisionReader.fetch_latest_decisions
-- Примечание: native event_class column отсутствует (scripts/fill_bid_decision.py INSERT).
-- ============================================================================
WITH latest_version AS (
    SELECT
        adv_id,
        nmid,
        norm_query,
        max(version) AS max_version
    FROM default_db.bid_decision_log
    WHERE adv_id IN {adv_ids:Array(Int32)}
      AND decision_time <= {package_cutoff_instant:DateTime}
      AND (
          stats_max_timestamp IS NULL
          OR stats_max_timestamp <= {package_cutoff_instant:DateTime}
      )
    GROUP BY adv_id, nmid, norm_query
),
rows_at_max AS (
    SELECT
        d.adv_id,
        d.nmid,
        d.norm_query,
        d.cpm_curr,
        d.final_bid,
        d.decision_time,
        d.stats_max_timestamp,
        d.decision_source,
        d.version
    FROM default_db.bid_decision_log AS d
    INNER JOIN latest_version AS lv
        ON d.adv_id = lv.adv_id
       AND d.nmid = lv.nmid
       AND d.norm_query = lv.norm_query
       AND d.version = lv.max_version
    WHERE d.decision_time <= {package_cutoff_instant:DateTime}
      AND (
          d.stats_max_timestamp IS NULL
          OR d.stats_max_timestamp <= {package_cutoff_instant:DateTime}
      )
)
SELECT
    adv_id,
    nmid,
    norm_query,
    max(version) AS version,
    uniqExact(
        (cpm_curr, final_bid, decision_time, stats_max_timestamp, decision_source, version)
    ) AS tuple_variants_at_max_version,
    any(
        (cpm_curr, final_bid, decision_time, stats_max_timestamp, decision_source, version)
    ) AS decision_tuple
FROM rows_at_max
GROUP BY adv_id, nmid, norm_query
