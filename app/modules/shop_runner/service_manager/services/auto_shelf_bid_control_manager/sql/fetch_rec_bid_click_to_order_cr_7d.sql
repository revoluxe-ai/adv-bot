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
--   %(mode)s      - режим текущего control-state
--   %(date_from)s - нижняя граница bucket_start окна (inclusive)
--   %(date_to)s   - верхняя граница bucket_start окна (exclusive)
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
  AND bucket_start >= %(date_from)s
  AND bucket_start < %(date_to)s
  AND delta_clicks IS NOT NULL
  AND delta_orders IS NOT NULL
  AND mode = %(mode)s
