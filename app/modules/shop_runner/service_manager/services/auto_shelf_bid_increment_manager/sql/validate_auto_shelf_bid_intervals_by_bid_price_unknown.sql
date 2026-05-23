-- ============================================================================
-- validate_auto_shelf_bid_intervals_by_bid_price_unknown.sql
-- ============================================================================
-- Назначение:
--   Сверка дельт по интервалам для nmid, когда цена в текущем снимке неизвестна
--   (хотя бы одно из price_minor / price_currency — NULL). Без фильтра по price
--   по датам и ставке в диапазоне.
--
-- Не вызывается в runtime update — отдельный файл от known-варианта (не комментарий
-- в одном SQL), чтобы явно различать режимы аналитики.
--
-- Параметры:
--   %(from_date)s, %(to_date)s, %(nmid)s
--
-- Дедуп:
--   Защита аналитики от физдублей по референсу:
--   GROUP BY event_date,event_id + argMax(..., version) во внутреннем слое.
--
-- Группировка снаружи: report_date, bid_minor, currency, price_minor, price_currency.
-- ============================================================================

SELECT
    toDate(dedup.src_ts) AS report_date,
    bid_minor,
    currency,
    price_minor,
    price_currency,
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
        argMax(src_ts, version) AS src_ts,
        argMax(bid_minor, version) AS bid_minor,
        argMax(currency, version) AS currency,
        argMax(price_minor, version) AS price_minor,
        argMax(price_currency, version) AS price_currency,
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
WHERE 1 = 1
GROUP BY report_date, bid_minor, currency, price_minor, price_currency
ORDER BY report_date DESC, bid_minor DESC, price_minor DESC
