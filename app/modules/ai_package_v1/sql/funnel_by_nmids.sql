-- ============================================================================
-- funnel_by_nmids.sql
-- ============================================================================
-- Назначение: funnel/common stat только по main_nmid из export scope (не shop-wide).
-- Таблица(и): default_db.wb_common_stat
-- Параметры: %(start_date)s, %(end_date)s, %(nmids)s
-- Вызывается: ChFunnelReader.fetch_rows_with_client
-- ============================================================================
SELECT
    nmid,
    toDate(date) AS stat_date,
    argMax(open_card, version) AS open_card,
    argMax(add_to_cart, version) AS add_to_cart,
    argMax(orders, version) AS orders,
    argMax(orders_sum, version) AS orders_sum,
    argMax(buy_outs, version) AS buy_outs
FROM default_db.wb_common_stat
WHERE nmid IN %(nmids)s
  AND toDate(date) BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
GROUP BY nmid, stat_date
ORDER BY nmid, stat_date
