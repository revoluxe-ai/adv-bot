-- ============================================================================
-- fetch_rec_bid_click_to_order_cr_7d.sql
-- ============================================================================
-- Назначение:
--   Вернуть 7d click-to-order CR для read-only PlanContext recommendation.
--   CR считается как sum(delta_orders) / sum(delta_clicks).
--
-- Таблица:
--   default_db.auto_shelf_bid_intervals
--
-- Параметры:
--   %(nmid)s      - артикул
--   %(mode)s      - режим текущего control-state; пустая строка = без фильтра
--   %(date_from)s - нижняя граница src_ts/bucket окна (inclusive)
--   %(date_to)s   - верхняя граница src_ts/bucket окна (exclusive)
--
-- Вызывается:
--   AutoShelfBidControlAnalyticsRepository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(...)
-- ============================================================================

SELECT
    if(sum(delta_clicks) > 0, sum(delta_orders) / sum(delta_clicks), 0.0) AS click_to_order_cr_7d,
    sum(delta_clicks) AS clicks,
    sum(delta_orders) AS orders
FROM default_db.auto_shelf_bid_intervals
WHERE nmid = %(nmid)s
  AND src_ts >= %(date_from)s
  AND src_ts < %(date_to)s
  AND delta_clicks IS NOT NULL
  AND delta_orders IS NOT NULL
  AND (%(mode)s = '' OR mode = %(mode)s)
