-- ============================================================================
-- keyword_position_bounds.sql
-- ============================================================================
-- Назначение: independent MIN/MAX для keyword_position_from_api (version ms cutoff).
-- Таблица(и): default_db.keyword_position_from_api
-- Параметры: nmids, package_cutoff_date, cutoff_instant_ms
-- Вызывается: ChKeywordBoundsReader.fetch_position_bounds
-- ============================================================================
SELECT
    min(date) AS position_first_available,
    max(date) AS position_last_available
FROM default_db.keyword_position_from_api
WHERE nmid IN {nmids:Array(Int32)}
  AND date <= {package_cutoff_date:Date}
  AND version <= {cutoff_instant_ms:UInt64}
