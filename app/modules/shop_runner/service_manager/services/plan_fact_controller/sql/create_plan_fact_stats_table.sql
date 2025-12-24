CREATE TABLE IF NOT EXISTS default_db.plan_fact_stats (
    adv_id Int32,
    shop_id LowCardinality(String),
    date Date,
    timestamp DateTime,
    plan_orders Nullable(Int32),
    plan_target_pay_for_order Nullable(Int32),
    plan_max_pay_for_order Nullable(Int32),
    fact_predict_orders Nullable(Float64),
    fact_original_orders Nullable(Float64),
    fact_pay_for_order Nullable(Float64),
    fact_method Nullable(String),
    version Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (adv_id, date, timestamp)
SETTINGS index_granularity = 8192;



