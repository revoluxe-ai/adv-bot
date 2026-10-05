-- campaign-settings-history: append-only canonical settings snapshots.
-- Applied only by scripts.clickhouse_migration_control_plane under existing gates.

CREATE TABLE IF NOT EXISTS default_db.campaign_settings_history
(
    observed_at DateTime64(3, 'UTC'),
    snapshot_id UUID,
    adv_setting_id UInt64,
    wb_cabinet_id UInt64,
    shop_id String,
    adv_id Nullable(UInt64),
    search_adv_id Nullable(UInt64),
    schema_version UInt16,
    state_hash FixedString(64),
    payload_json String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(observed_at)
ORDER BY (wb_cabinet_id, adv_setting_id, observed_at, snapshot_id);
