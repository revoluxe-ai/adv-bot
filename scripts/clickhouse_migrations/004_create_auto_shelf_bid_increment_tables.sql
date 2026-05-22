-- ============================================================================
-- Migration: Auto shelf bid incremental tables
-- Description:
--   1) Interval deltas for recommendations/shelf traffic by nmid + bid + price
--   2) Prev snapshot fallback storage
-- Notes:
--   - V1 has no revenue columns by design
--   - price_minor starts as Nullable(Int64), can be switched to Int64 DEFAULT 0
--     if insert-path/driver compatibility issues appear
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.auto_shelf_bid_intervals
(
    event_date Date DEFAULT toDate(src_ts),
    event_id String,
    src_ts DateTime,
    bucket_start DateTime,
    version UInt64,

    nmid UInt64,
    mode String,

    bid_minor Int64,
    currency String DEFAULT 'RUB',

    price_minor Nullable(Int64),
    price_currency String DEFAULT 'RUB',

    delta_impressions Int64,
    delta_clicks Int64,
    delta_carts Int64,
    delta_orders Int64,
    delta_spend Float64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (nmid, event_date, bucket_start, mode, bid_minor, currency, price_currency, event_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS default_db.auto_shelf_bid_prev
(
    nmid UInt64,

    src_ts DateTime,
    version UInt64,

    mode String,

    bid_minor Int64,
    currency String DEFAULT 'RUB',

    price_minor Nullable(Int64),
    price_currency String DEFAULT 'RUB',

    impressions UInt64,
    clicks UInt64,
    carts UInt64,
    orders UInt64,
    spend Float64
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (nmid)
SETTINGS index_granularity = 8192;

