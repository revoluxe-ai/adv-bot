-- ============================================================================
-- insert_auto_shelf_bid_interval.sql
-- ============================================================================
-- Назначение:
--   Вставить одну строку инкрементального интервала (дельта метрик полок
--   между prev и current snapshot за 5-минутный bucket).
--
-- Таблица: default_db.auto_shelf_bid_intervals
--   Ключ сегмента: nmid + mode + bid_minor + currency + price_* + bucket/version.
--
-- Параметры: поля AutoShelfBidIntervalRow (event_date, event_id, src_ts,
--   bucket_start, version, nmid, mode, bid_minor, currency, price_minor,
--   price_currency, delta_impressions … delta_spend).
--
-- Вызывается: ClickHouseAutoShelfBidWriter.insert_interval после расчёта delta.
--
-- Идемпотентность:
--   Повторный тик с тем же event_id (например, после partial-failure между
--   interval insert и persist prev) не должен создавать вторую строку.
--   Для этого используется INSERT ... SELECT ... WHERE NOT EXISTS по
--   (event_date, event_id).
-- ============================================================================

INSERT INTO default_db.auto_shelf_bid_intervals (
    event_date,
    event_id,
    src_ts,
    bucket_start,
    version,
    nmid,
    mode,
    bid_minor,
    currency,
    price_minor,
    price_currency,
    delta_impressions,
    delta_clicks,
    delta_carts,
    delta_orders,
    delta_spend
)
SELECT
    %(event_date)s,
    %(event_id)s,
    %(src_ts)s,
    %(bucket_start)s,
    %(version)s,
    %(nmid)s,
    %(mode)s,
    %(bid_minor)s,
    %(currency)s,
    %(price_minor)s,
    %(price_currency)s,
    %(delta_impressions)s,
    %(delta_clicks)s,
    %(delta_carts)s,
    %(delta_orders)s,
    %(delta_spend)s
WHERE NOT EXISTS (
    SELECT 1
    FROM default_db.auto_shelf_bid_intervals
    WHERE event_date = %(event_date)s
      AND event_id = %(event_id)s
)
