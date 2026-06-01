-- ============================================================================
-- get_prev_auto_shelf_bid.sql
-- ============================================================================
-- Назначение:
--   Прочитать последний сохранённый снимок (prev) для nmid из ClickHouse.
--   Используется LastAutoShelfBidStateManager при промахе Redis.
--
-- Таблица: default_db.auto_shelf_bid_prev (ReplacingMergeTree по version)
--
-- Параметры:
--   %(nmid)s — артикул
--
-- Логика:
--   ORDER BY version DESC LIMIT 1 — актуальная версия снимка.
--   bucket_start в таблице нет; repository подставляет bucket_start = src_ts.
-- ============================================================================

SELECT
    nmid,
    src_ts,
    version,
    mode,
    bid_minor,
    currency,
    price_minor,
    price_currency,
    impressions,
    clicks,
    carts,
    orders,
    spend
FROM default_db.auto_shelf_bid_prev
WHERE nmid = %(nmid)s
ORDER BY version DESC
LIMIT 1
