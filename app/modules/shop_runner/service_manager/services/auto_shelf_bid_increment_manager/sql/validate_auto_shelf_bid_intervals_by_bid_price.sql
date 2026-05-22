-- ============================================================================
-- validate_auto_shelf_bid_intervals_by_bid_price.sql
-- ============================================================================
-- Назначение:
--   Аналитическая сверка накопленных дельт по интервалам для nmid, когда цена
--   известна (оба price_minor и price_currency заданы у текущего снимка).
--
-- Не вызывается в runtime update — используется вручную / в unit-тестах контракта.
--
-- Параметры:
--   %(from_date)s, %(to_date)s — диапазон event_date
--   %(nmid)s — артикул
--   %(current_price_minor)s, %(current_price_currency)s — текущая известная цена
--
-- Фильтр цены (wildcard для legacy/unknown строк в CH):
--   (price совпадает с текущей known) OR price_minor IS NULL OR price_currency IS NULL
--   — чтобы не терять интервалы с неизвестной ценой при сверке known-сегмента.
--
-- Группировка: report_date (toDate(src_ts)), bid_minor, currency, price_*.
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
  AND (
    (price_minor = %(current_price_minor)s AND price_currency = %(current_price_currency)s)
    OR price_minor IS NULL
    OR price_currency IS NULL
  )
GROUP BY report_date, bid_minor, currency, price_minor, price_currency
ORDER BY report_date DESC, bid_minor DESC, price_minor DESC
