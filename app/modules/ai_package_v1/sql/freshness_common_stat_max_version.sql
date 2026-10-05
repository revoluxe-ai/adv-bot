-- ============================================================================
-- freshness_common_stat_max_version.sql
-- ============================================================================
-- Назначение: сигнал freshness для funnel (max version по nmids), не coverage.
-- Таблица(и): default_db.wb_common_stat
-- Параметры: %(nmids)s
-- Вызывается: ChExportFreshnessReader.max_common_stat_version
-- ============================================================================
SELECT max(version) AS max_mv
FROM default_db.wb_common_stat
WHERE nmid IN %(nmids)s
