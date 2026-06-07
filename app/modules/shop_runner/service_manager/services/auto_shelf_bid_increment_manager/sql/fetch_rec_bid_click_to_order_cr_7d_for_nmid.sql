-- ============================================================================
-- fetch_rec_bid_click_to_order_cr_7d_for_nmid.sql
-- ============================================================================
-- Назначение:
--   Вернуть click_to_order_cr_7d для rec bid pipeline по bucket-строкам
--   из default_db.auto_shelf_bid_intervals.
--   Метрика считается как sum(delta_orders) / nullIf(sum(delta_clicks), 0).
--
-- Таблица:
--   default_db.auto_shelf_bid_intervals
--
-- Параметры:
--   %(nmid)s      - артикул
--   %(mode)s      - режим кампании
--   %(date_from)s - нижняя граница bucket_start (inclusive)
--   %(date_to)s   - верхняя граница bucket_start (exclusive)
--
-- Вызывается:
--   AutoShelfBidRepository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(...)
-- ============================================================================

SELECT
    if(
        sum(delta_clicks) = 0,
        0.0,
        sum(delta_orders) / sum(delta_clicks)
    ) AS click_to_order_cr_7d
FROM default_db.auto_shelf_bid_intervals
WHERE nmid = %(nmid)s
  AND mode = %(mode)s
  AND bucket_start >= %(date_from)s
  AND bucket_start < %(date_to)s
