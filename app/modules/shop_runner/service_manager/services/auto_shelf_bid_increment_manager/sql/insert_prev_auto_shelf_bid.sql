-- ============================================================================
-- insert_prev_auto_shelf_bid.sql
-- ============================================================================
-- Назначение:
--   Записать текущий снимок метрик полок в prev-таблицу (источник истины в CH).
--   Вызывается после каждого успешного persist в Redis (LastAutoShelfBidStateManager).
--
-- Таблица: default_db.auto_shelf_bid_prev
--   ReplacingMergeTree: при совпадении ключа более новая version заменяет старую.
--
-- Параметры: поля AutoShelfBidSnapshot (nmid, src_ts, version, mode, bid_minor,
--   currency, price_minor, price_currency, impressions, clicks, carts, orders, spend).
-- ============================================================================

INSERT INTO default_db.auto_shelf_bid_prev (
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
)
VALUES (
    %(nmid)s,
    %(src_ts)s,
    %(version)s,
    %(mode)s,
    %(bid_minor)s,
    %(currency)s,
    %(price_minor)s,
    %(price_currency)s,
    %(impressions)s,
    %(clicks)s,
    %(carts)s,
    %(orders)s,
    %(spend)s
)
