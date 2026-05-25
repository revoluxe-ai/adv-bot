-- ============================================================================
-- get_bid_stats_dedup.sql
-- ============================================================================
-- Назначение:
--   Агрегат по точке ставки (bid_minor) из intervals с read-time dedup.
--   mode не входит в GROUP BY: пассивный main и test на одной ставке — одна строка.
--
-- Таблица: default_db.auto_shelf_bid_intervals
-- Параметры:
--   %(nmid)s, %(from_ts)s, %(currency)s
--   %(mode)s (nullable) — опциональный фильтр до агрегации
--   %(bid_minor)s (nullable)
-- Вызывается:
--   AutoShelfBidControlAnalyticsRepository.get_bid_stats()
-- ============================================================================

SELECT
    dedup.bid_minor AS bid_minor,
    dedup.currency AS currency,
    CAST(NULL AS Nullable(String)) AS mode,
    sum(dedup.delta_impressions) AS impressions,
    sum(dedup.delta_clicks) AS clicks,
    sum(dedup.delta_carts) AS carts,
    sum(dedup.delta_orders) AS orders,
    sum(dedup.delta_spend) AS spend,
    max(dedup.src_ts) AS last_interval_at
FROM
(
    SELECT
        event_date,
        event_id,
        argMax(src_ts, version) AS src_ts,
        argMax(mode, version) AS mode,
        argMax(bid_minor, version) AS bid_minor,
        argMax(currency, version) AS currency,
        argMax(delta_impressions, version) AS delta_impressions,
        argMax(delta_clicks, version) AS delta_clicks,
        argMax(delta_carts, version) AS delta_carts,
        argMax(delta_orders, version) AS delta_orders,
        argMax(delta_spend, version) AS delta_spend
    FROM default_db.auto_shelf_bid_intervals AS i
    WHERE i.nmid = %(nmid)s
      AND i.src_ts >= %(from_ts)s
      AND i.currency = %(currency)s
    GROUP BY event_date, event_id
) AS dedup
WHERE (%(mode)s IS NULL OR dedup.mode = %(mode)s)
  AND (%(bid_minor)s IS NULL OR dedup.bid_minor = %(bid_minor)s)
GROUP BY dedup.bid_minor, dedup.currency
ORDER BY last_interval_at DESC, dedup.bid_minor ASC
