-- ============================================================================
-- fetch_auto_shelf_bid_bucket_rows.sql
-- ============================================================================
-- Назначение:
--   Отдать сырые 15-минутные bucket-строки из auto_shelf_bid_intervals для сборки
--   hour-level наблюдений в repository/read-layer.
--
-- Таблица:
--   default_db.auto_shelf_bid_intervals
--
-- Параметры:
--   %(nmid)s      - артикул
--   %(date_from)s - нижняя граница bucket_start (inclusive)
--   %(date_to)s   - верхняя граница bucket_start (exclusive)
--
-- Вызывается:
--   AutoShelfBidRepository.fetch_rec_bid_bucket_observations_for_nmid(...)
-- ============================================================================

SELECT
    event_id,
    version,
    bucket_start,
    bid_minor,
    price_minor,
    delta_impressions,
    delta_clicks,
    delta_orders,
    delta_spend
FROM default_db.auto_shelf_bid_intervals
WHERE nmid = %(nmid)s
  AND bucket_start >= %(date_from)s
  AND bucket_start < %(date_to)s
  AND delta_impressions IS NOT NULL
ORDER BY bucket_start ASC
