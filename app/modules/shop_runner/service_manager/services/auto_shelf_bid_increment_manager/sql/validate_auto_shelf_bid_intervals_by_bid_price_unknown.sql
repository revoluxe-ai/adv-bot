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
-- Группировка: report_date, bid_minor, currency, price_minor, price_currency.
-- ============================================================================

SELECT
    toDate(src_ts) AS report_date,
    bid_minor,
    currency,
    price_minor,
    price_currency,
    sum(delta_impressions) AS delta_impressions,
    sum(delta_clicks) AS delta_clicks,
    sum(delta_carts) AS delta_carts,
    sum(delta_orders) AS delta_orders,
    sum(delta_spend) AS delta_spend
FROM default_db.auto_shelf_bid_intervals
WHERE event_date >= %(from_date)s
  AND event_date <= %(to_date)s
  AND nmid = %(nmid)s
GROUP BY report_date, bid_minor, currency, price_minor, price_currency
ORDER BY report_date DESC, bid_minor DESC, price_minor DESC
