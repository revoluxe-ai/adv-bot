-- ============================================================================
-- get_keyword_earliest_date.sql
-- ============================================================================
-- Назначение: возвращает первую дату, доступную для дневной истории одного
--             ключевого запроса.
-- Таблица(и): default_db.mv_clusters_daily_agg, default_db.clusters_adv_stats
-- Параметры: %(text)s — ключевой запрос; %(adv_ids)s — список adv_id;
--            %(nmids)s — список артикулов WB
-- Вызывается: KeywordDailyHistoryManager.get_earliest_date
-- ============================================================================

SELECT MIN(date) AS earliest_date
FROM default_db.mv_clusters_daily_agg
WHERE adv_id IN %(adv_ids)s
  AND nmid IN %(nmids)s
  AND norm_query = %(text)s
