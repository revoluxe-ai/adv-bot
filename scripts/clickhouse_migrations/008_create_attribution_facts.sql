-- attribution-facts-contract Slice C: append-only observations + reconciliation metadata.
-- Applied only by scripts.clickhouse_migration_control_plane under existing gates.
-- No campaign-day spend columns (full_adv_wb_stat remains spend authority).

CREATE TABLE IF NOT EXISTS default_db.attribution_fact_observations
(
    shop_id String,
    physical_adv_id UInt64,
    event_date Date,
    app_type UInt8,
    ordered_nm_id UInt64,
    source_family LowCardinality(String),
    observation_id FixedString(32),
    source_revision UInt64,
    ingested_at DateTime64(3, 'UTC'),
    attribution_class LowCardinality(String),
    attributed_orders Nullable(Int64),
    attributed_gmv_rub Nullable(Decimal(18, 2)),
    attributed_atc Nullable(Int64),
    attributed_units_shks Nullable(Int64),
    membership_snapshot_id String,
    partial_membership_fallback UInt8
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (
    shop_id,
    physical_adv_id,
    event_date,
    app_type,
    ordered_nm_id,
    source_revision,
    ingested_at,
    observation_id
);

CREATE TABLE IF NOT EXISTS default_db.attribution_day_reconciliation
(
    shop_id String,
    physical_adv_id UInt64,
    event_date Date,
    passed UInt8,
    nm_orders_sum Int64,
    day_orders Int64,
    nm_gmv_sum Decimal(18, 2),
    day_gmv_rub Decimal(18, 2),
    unattributed_orders Int64,
    reason_codes Array(String),
    source_revision UInt64,
    ingested_at DateTime64(3, 'UTC')
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (
    shop_id,
    physical_adv_id,
    event_date,
    source_revision,
    ingested_at
);
