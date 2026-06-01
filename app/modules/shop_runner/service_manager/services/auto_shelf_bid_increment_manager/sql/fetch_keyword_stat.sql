-- ============================================================================
-- fetch_keyword_stat.sql
-- ============================================================================
-- Назначение:
--   Суммарная статистика по ключевым словам (кластерам / norm_query) для одной
--   Auto-РК и одного nmid за отчётный день (today Moscow, report_date).
--
-- Используется в auto_shelf_bid_increment_manager:
--   recommendations_stat = total_auto_stat - keyword_stat
--   (полки/рекомендации = всё по Auto минус поисковые кластеры).
--
-- Источник: default_db.clusters_adv_stats
--   Одна строка = метрики по паре (adv_id, nmid, norm_query) на момент timestamp.
--   Поле add_to_cart в CH маппится в DTO как carts (как added_to_cart в full_adv_wb_stat).
--
-- Параметры:
--   %(report_date)s  — дата отчёта (строка YYYY-MM-DD, Europe/Moscow «сегодня»)
--   %(auto_adv_id)s  — ID Auto-кампании (ComplexAdv.auto_adv_id)
--   %(nmid)s         — артикул (для v1: единственный nmid из ComplexAdv)
--
-- Если строк нет: запрос возвращает пустой result_set → repository даёт None,
-- менеджер трактует keyword как ноль (`keyword_stat_missing_treated_as_zero`).
-- Для полочной Auto-РК без показов по ключам это ожидаемый сценарий.
-- ============================================================================

-- По каждому ключевому слову (norm_query) берём последнюю версию метрик за день:
-- argMax(metric, timestamp) — как в остальных CH-агрегациях проекта.
WITH latest_per_keyword AS (
    SELECT
        norm_query,
        argMax(views, timestamp) AS views,
        argMax(clicks, timestamp) AS clicks,
        argMax(add_to_cart, timestamp) AS carts,
        argMax(orders, timestamp) AS orders,
        argMax(spend, timestamp) AS spend
    FROM default_db.clusters_adv_stats
    WHERE date = %(report_date)s
      AND adv_id = %(auto_adv_id)s
      AND nmid = %(nmid)s
    GROUP BY norm_query
)

-- Складываем все кластеры в один итог по Auto (keyword-часть дня).
SELECT
    COALESCE(SUM(toInt64(views)), 0) AS impressions,
    COALESCE(SUM(toInt64(clicks)), 0) AS clicks,
    COALESCE(SUM(toInt64(carts)), 0) AS carts,
    COALESCE(SUM(toInt64(orders)), 0) AS orders,
    COALESCE(SUM(toFloat64(spend)), 0.0) AS spend
FROM latest_per_keyword
