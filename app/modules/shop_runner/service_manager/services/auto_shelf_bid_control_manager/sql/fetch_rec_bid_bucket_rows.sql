-- ============================================================================
-- fetch_rec_bid_bucket_rows.sql
-- ============================================================================
-- Назначение:
--   Отдать 15-минутные bucket-строки для read-only rec bid recommendation.
--
-- Таблица:
--   default_db.auto_shelf_bid_intervals
--
-- Параметры:
--   %(nmid)s      - артикул
--   %(mode)s      - режим текущего control-state; пустая строка = без фильтра
--   %(date_from)s - нижняя граница bucket_start (inclusive)
--   %(date_to)s   - верхняя граница bucket_start (exclusive)
--
-- Вызывается:
--   AutoShelfBidControlAnalyticsRepository.fetch_rec_bid_bucket_observations_for_nmid(...)
-- ============================================================================

SELECT
    event_id,
    version,
    mode,
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
  AND (%(mode)s = '' OR mode = %(mode)s)
ORDER BY bucket_start ASC
