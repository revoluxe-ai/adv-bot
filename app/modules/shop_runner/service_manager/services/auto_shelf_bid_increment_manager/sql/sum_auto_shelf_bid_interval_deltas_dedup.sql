-- ============================================================================
-- sum_auto_shelf_bid_interval_deltas_dedup.sql
-- ============================================================================
-- Назначение:
--   Дедуплицированная сумма дельт по интервалам auto_shelf для диапазона дат.
--   Используется для аналитической сверки, чтобы физические дубли event_id не
--   задваивали итоговые метрики.
--
-- Таблица: default_db.auto_shelf_bid_intervals
-- Параметры:
--   %(from_date)s, %(to_date)s — диапазон event_date
--   %(nmid)s — артикул
-- Вызывается: ручная проверка / unit tests контракта дедупа
-- ============================================================================

SELECT
    sum(dedup.delta_impressions) AS delta_impressions,
    sum(dedup.delta_clicks) AS delta_clicks,
    sum(dedup.delta_carts) AS delta_carts,
    sum(dedup.delta_orders) AS delta_orders,
    sum(dedup.delta_spend) AS delta_spend
FROM
(
    SELECT
        event_date,
        event_id,
        argMax(delta_impressions, version) AS delta_impressions,
        argMax(delta_clicks, version) AS delta_clicks,
        argMax(delta_carts, version) AS delta_carts,
        argMax(delta_orders, version) AS delta_orders,
        argMax(delta_spend, version) AS delta_spend
    FROM default_db.auto_shelf_bid_intervals
    WHERE event_date >= %(from_date)s
      AND event_date <= %(to_date)s
      AND nmid = %(nmid)s
    GROUP BY event_date, event_id
) AS dedup
