-- ============================================================================
-- keyword_history_bounds.sql
-- ============================================================================
-- Назначение: MIN/MAX date bounds для clusters_adv_stats с package cutoff.
-- Таблица(и): default_db.clusters_adv_stats
-- Параметры: adv_ids, package_cutoff_date, package_cutoff_instant
-- Вызывается: ChKeywordBoundsReader.fetch_daily_bounds
-- ============================================================================
SELECT
    min(date) AS first_available,
    max(date) AS last_available
FROM default_db.clusters_adv_stats
WHERE adv_id IN {adv_ids:Array(Int32)}
  AND date <= {package_cutoff_date:Date}
  AND timestamp <= {package_cutoff_instant:DateTime}
