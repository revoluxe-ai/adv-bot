-- ============================================================================
-- Migration: Add event_date and event_id to fact_stat_states
-- Date: 2026-02-07
-- Description: Application code (INSERT and sum_fact_state_deltas.sql) uses
--   event_date and event_id; without these columns INSERT fails with
--   "unknown column" and the SELECT WHERE/GROUP BY fail.
--   - CREATE TABLE IF NOT EXISTS: ensures new envs get the full schema.
--   - ALTER ADD COLUMN IF NOT EXISTS: adds columns to existing tables.
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.fact_stat_states (
    bucket_start DateTime,
    shop_id String,
    complex_adv_id Int64,
    views_adv_sum Int64,
    clicks_adv_sum Int64,
    carts_adv_sum Int64,
    orders_adv_sum Int64,
    spend_adv_sum_rub Int64,
    orders_sum_adv_rub Int64,
    open_card_sum Int64,
    carts_card_sum Int64,
    orders_card_sum Int64,
    orders_sum_card_rub Int64,
    buy_outs_sum Int64,
    src_ts DateTime,
    version Int64,
    event_date Date DEFAULT toDate(0),
    event_id Int64 DEFAULT 0
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (complex_adv_id, event_date, event_id, src_ts)
SETTINGS index_granularity = 8192;

-- Add columns to existing tables that were created without them (no-op if already present)
ALTER TABLE default_db.fact_stat_states
    ADD COLUMN IF NOT EXISTS event_date Date DEFAULT toDate(0),
    ADD COLUMN IF NOT EXISTS event_id Int64 DEFAULT 0;
