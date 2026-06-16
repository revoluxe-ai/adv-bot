-- ============================================================================
-- get_keyword_daily_history.sql
-- ============================================================================
-- Назначение: возвращает посуточно агрегированную историю по одному
--             ключевому запросу с позициями и CPM.
-- Таблица(и): default_db.mv_clusters_daily_agg, default_db.clusters_adv_stats
-- Параметры: %(text)s — ключевой запрос; %(adv_ids)s — список adv_id;
--            %(nmids)s — список артикулов WB; %(start_date)s / %(end_date)s —
--            границы страницы по датам
-- Вызывается: KeywordDailyHistoryManager._load_history_rows
-- ============================================================================

WITH daily_last AS (
    SELECT
        date,
        sum(views0) AS views,
        sum(clicks0) AS clicks,
        sum(add_to_cart0) AS add_to_cart,
        sum(orders0) AS orders,
        sum(cpm0 * views0) / 1000.0 AS spend,
        if(sum(views0) > 0, sum(cpm0 * views0) / sum(views0), 0.0) AS cpm
    FROM
    (
        SELECT
            date,
            argMaxMerge(views_state) AS views0,
            argMaxMerge(clicks_state) AS clicks0,
            argMaxMerge(carts_state) AS add_to_cart0,
            argMaxMerge(orders_state) AS orders0,
            argMaxMerge(cpm_state) AS cpm0
        FROM default_db.mv_clusters_daily_agg
        WHERE adv_id IN %(adv_ids)s
          AND nmid IN %(nmids)s
          AND norm_query = %(text)s
          AND date >= %(start_date)s
          AND date <= %(end_date)s
        GROUP BY
            adv_id,
            nmid,
            norm_query,
            date
    )
    GROUP BY date
),
position_by_day AS (
    SELECT
        date,
        avgIf(avr_pos, avr_pos > 0) AS avg_pos
    FROM default_db.clusters_adv_stats
    WHERE adv_id IN %(adv_ids)s
      AND nmid IN %(nmids)s
      AND norm_query = %(text)s
      AND date >= %(start_date)s
      AND date <= %(end_date)s
    GROUP BY date
)
SELECT
    daily_last.date,
    daily_last.views,
    daily_last.clicks,
    daily_last.add_to_cart,
    daily_last.orders,
    daily_last.spend,
    daily_last.cpm,
    coalesce(position_by_day.avg_pos, 0.0) AS avg_pos
FROM daily_last
LEFT JOIN position_by_day USING (date)
ORDER BY daily_last.date DESC
