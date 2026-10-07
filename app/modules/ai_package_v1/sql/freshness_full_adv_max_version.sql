-- ============================================================================
-- freshness_full_adv_max_version.sql
-- ============================================================================
-- Назначение: сигнал freshness для campaign stat (max version), не coverage.
-- Таблица(и): default_db.full_adv_wb_stat
-- Параметры: %(adv_ids)s
-- Вызывается: ChExportFreshnessReader.max_full_adv_version
-- ============================================================================
SELECT max(max_version) AS max_mv
FROM (
    SELECT adv_id, max(version) AS max_version
    FROM default_db.full_adv_wb_stat
    WHERE adv_id IN %(adv_ids)s
    GROUP BY adv_id
)
