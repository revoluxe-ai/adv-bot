-- ============================================================================
-- get_impressions_for_mode_bid.sql
-- ============================================================================
-- Назначение:
--   Показы по ставке (bid_minor) с дедупом; mode опционален.
--   %(mode)s IS NULL — все mode (test+main): пассивный/legacy main на той же ставке.
--
-- Таблица: default_db.auto_shelf_bid_intervals
-- Параметры:
--   %(nmid)s, %(from_ts)s, %(currency)s, %(mode)s (nullable), %(bid_minor)s
-- Вызывается:
--   AutoShelfBidControlAnalyticsRepository.get_impressions()
-- ============================================================================

SELECT
    coalesce(sum(dedup.delta_impressions), 0) AS impressions
FROM
(
    SELECT
        event_date,
        event_id,
        argMax(src_ts, version) AS src_ts,
        argMax(mode, version) AS mode,
        argMax(bid_minor, version) AS bid_minor,
        argMax(currency, version) AS currency,
        argMax(delta_impressions, version) AS delta_impressions
    FROM default_db.auto_shelf_bid_intervals AS i
    WHERE i.nmid = %(nmid)s
      AND i.src_ts >= %(from_ts)s
      AND i.currency = %(currency)s
    GROUP BY event_date, event_id
) AS dedup
WHERE dedup.bid_minor = %(bid_minor)s
  AND (%(mode)s IS NULL OR dedup.mode = %(mode)s)

