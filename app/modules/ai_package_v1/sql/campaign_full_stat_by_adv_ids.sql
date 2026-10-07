-- ============================================================================
-- campaign_full_stat_by_adv_ids.sql
-- ============================================================================
-- Назначение: дневная campaign full stat по списку adv_id за период (без слияния Auto/Search).
-- Таблица(и): default_db.full_adv_wb_stat
-- Параметры: %(start_date)s, %(end_date)s, %(adv_ids)s
-- Вызывается: ChCampaignStatReader.fetch_rows_with_client
-- ============================================================================
SELECT
    adv_id,
    date,
    argMax(views, version) AS views,
    argMax(clicks, version) AS clicks
FROM default_db.full_adv_wb_stat
WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
  AND adv_id IN %(adv_ids)s
GROUP BY adv_id, date
ORDER BY adv_id, date
