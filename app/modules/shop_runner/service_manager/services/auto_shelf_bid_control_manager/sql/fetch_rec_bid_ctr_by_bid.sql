-- ============================================================================
-- fetch_rec_bid_ctr_by_bid.sql
-- ============================================================================
-- Назначение:
--   Вернуть реальный CTR по bid на основе bucket-строк из auto_shelf_bid_intervals.
--   CTR считается как sum(delta_clicks) / sum(delta_impressions) по каждому bid.
--
-- Таблица:
--   default_db.auto_shelf_bid_intervals
--
-- Параметры:
--   %(nmid)s      - артикул
--   mode          - режим анализа; None = all modes / без фильтра
--   %(date_from)s - нижняя граница bucket_start (inclusive)
--   %(date_to)s   - верхняя граница bucket_start (exclusive)
--
-- Вызывается:
--   AutoShelfBidControlAnalyticsRepository.fetch_rec_bid_ctr_by_bid_for_nmid(...)
-- ============================================================================

SELECT
    bid_minor AS bid,
    sum(delta_impressions) AS impressions,
    sum(delta_clicks) AS clicks
FROM default_db.auto_shelf_bid_intervals
WHERE nmid = %(nmid)s
  AND bucket_start >= %(date_from)s
  AND bucket_start < %(date_to)s
  AND delta_impressions IS NOT NULL
  -- MODE_FILTER
GROUP BY bid_minor
ORDER BY bid_minor ASC
