-- ============================================================================
-- get_best_bid_by_cart_cpa.sql
-- ============================================================================
-- Назначение:
--   Лучшая ставка (минимальный cart_cpa) по точке bid_minor.
--   При carts=0 в знаменателе 1 корзина: spend / greatest(carts, 1).
--   Метрики суммируются по всем mode на одной ставке.
--
-- Таблица: default_db.auto_shelf_bid_intervals
-- Параметры:
--   %(nmid)s, %(from_ts)s, %(currency)s
-- Вызывается:
--   AutoShelfBidControlAnalyticsRepository.get_best_bid_by_cart_cpa()
-- ============================================================================

SELECT
    stats.bid_minor AS bid_minor,
    stats.currency AS currency,
    CAST(NULL AS Nullable(String)) AS mode,
    stats.impressions AS impressions,
    stats.clicks AS clicks,
    stats.carts AS carts,
    stats.orders AS orders,
    stats.spend AS spend
FROM
(
    SELECT
        dedup.bid_minor AS bid_minor,
        dedup.currency AS currency,
        sum(dedup.delta_impressions) AS impressions,
        sum(dedup.delta_clicks) AS clicks,
        sum(dedup.delta_carts) AS carts,
        sum(dedup.delta_orders) AS orders,
        sum(dedup.delta_spend) AS spend
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
    GROUP BY dedup.bid_minor, dedup.currency
) AS stats
WHERE stats.impressions > 0
ORDER BY (stats.spend / greatest(stats.carts, 1)) ASC, stats.bid_minor ASC
LIMIT 1
