-- ============================================================================
-- fetch_total_auto_stat.sql
-- ============================================================================
-- Назначение:
--   Суммарная дневная статистика по всей Auto-РК (без разбиения на полки/поиск).
--   Это «верхняя» часть формулы: recommendations_stat = total_auto - keyword.
--
-- Источник: default_db.full_adv_wb_stat
--   Одна строка = снимок метрик adv_id на момент version.
--   added_to_cart в CH → carts в результате.
--
-- Параметры:
--   %(report_date)s  — дата отчёта (YYYY-MM-DD, Europe/Moscow)
--   %(auto_adv_id)s  — ID Auto-кампании
--
-- Агрегация:
--   CTE latest: argMax(metric, version) по adv_id за день.
--   Итог: одна строка impressions/clicks/carts/orders/spend.
--
-- Если строк нет: пустой result_set → repository None → update прерывается.
-- ============================================================================

WITH latest AS (
    SELECT
        adv_id,
        argMax(views, version) AS views,
        argMax(clicks, version) AS clicks,
        argMax(added_to_cart, version) AS carts,
        argMax(orders, version) AS orders,
        argMax(spend, version) AS spend
    FROM default_db.full_adv_wb_stat
    WHERE date = %(report_date)s
      AND adv_id = %(auto_adv_id)s
    GROUP BY adv_id
)
SELECT
    COALESCE(SUM(toInt64(views)), 0) AS impressions,
    COALESCE(SUM(toInt64(clicks)), 0) AS clicks,
    COALESCE(SUM(toInt64(carts)), 0) AS carts,
    COALESCE(SUM(toInt64(orders)), 0) AS orders,
    COALESCE(SUM(toFloat64(spend)), 0.0) AS spend
FROM latest
