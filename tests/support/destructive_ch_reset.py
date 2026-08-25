"""ClickHouse session DDL + function-scoped table cleanup для destructive tests.

DDL выполняется один раз на session (через lifecycle). Per-test isolation —
TRUNCATE только test-owned tables в ``test_adv_bot_clickhouse``.
"""

from __future__ import annotations

from typing import Any

from tests.support.destructive_clickhouse import ALLOWED_CH_DATABASE

# Test-owned tables (без MV — TRUNCATE базовых таблиц достаточен для isolation).
CH_TEST_OWNED_TABLES: tuple[str, ...] = (
    "full_adv_wb_stat",
    "advkeyword_new",
    "clusters_adv_stats",
    "adv_events_ticks",
    "wb_common_stat",
    "plan_fact_stats",
    "fact_stat_states",
    "advkeyword",
)


def qualified_ch_table(name: str) -> str:
    """Полностью квалифицированное имя таблицы в allowed test DB."""
    return f"{ALLOWED_CH_DATABASE}.{name}"


# DDL statements — полностью квалифицированные, без USE / default_db.
CH_SESSION_DDL_STATEMENTS: tuple[str, ...] = (
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.full_adv_wb_stat (
            adv_id Int32,
            date Date,
            views Int32,
            clicks Int32,
            spend Float64,
            added_to_cart Int32,
            orders Int32,
            sum_price_orders Float64,
            version Float64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, version)
    """,
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.advkeyword_new (
            adv_id Int32,
            text String,
            date Date,
            clicks_state AggregateFunction(argMax, Int32, Float64),
            views_state AggregateFunction(argMax, Int32, Float64),
            spend_state AggregateFunction(argMax, Float64, Float64),
        ) ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, text, date)
        SETTINGS allow_dimensions_outside_sorting_key = 1, index_granularity = 8192
    """,
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.clusters_adv_stats (
            adv_id UInt32,
            nmid UInt64,
            wb_category LowCardinality(String),
            norm_query LowCardinality(String),
            views UInt32,
            clicks UInt32,
            ctr Float64,
            cpm Float64,
            add_to_cart UInt32,
            orders UInt32,
            cpc Float64,
            avr_pos Float64,
            date Date,
            spend Nullable(Float64) DEFAULT NULL,
            timestamp DateTime default now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (wb_category, nmid, norm_query, date, timestamp)
        SETTINGS index_granularity = 8192
    """,
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.adv_events_ticks (
            norm_query LowCardinality(String),
            ts DateTime,
            d_views UInt32,
            d_clicks UInt32,
            nmid UInt64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(ts)
        ORDER BY (norm_query, nmid, ts)
        SETTINGS index_granularity = 8192
    """,
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.wb_common_stat (
            nmid UInt64,
            date Date,
            open_card UInt32,
            add_to_cart UInt32,
            orders UInt32,
            orders_sum Float64,
            buy_outs UInt32,
            buyouts_sum_rub Float64 DEFAULT 0,
            version Float64,
            INDEX idx_wb_common_stat_date date TYPE minmax GRANULARITY 1
        )
        ENGINE = ReplacingMergeTree(version)
        ORDER BY (nmid, date)
        SETTINGS index_granularity = 8192
    """,
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.plan_fact_stats (
            adv_id Int32,
            shop_id String,
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
        SETTINGS index_granularity = 8192
    """,
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.fact_stat_states (
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
        SETTINGS index_granularity = 8192
    """,
    f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_CH_DATABASE}.advkeyword (
            adv_id UInt64,
            date Date,
            text String,
            views UInt32,
            clicks UInt32,
            spend Float64,
            version UInt64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, text, version)
        SETTINGS index_granularity = 8192
    """,
    f"DROP VIEW IF EXISTS {ALLOWED_CH_DATABASE}.advkeyword_daily_mv",
    f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {ALLOWED_CH_DATABASE}.advkeyword_daily_mv
        (
            `adv_id` UInt64,
            `date` Date,
            `text` String,
            `clicks` AggregateFunction(argMax, UInt32, UInt64),
            `views` AggregateFunction(argMax, UInt32, UInt64),
            `spend` AggregateFunction(argMax, Float64, UInt64)
        )
        ENGINE = AggregatingMergeTree
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, text)
        SETTINGS index_granularity = 8192
        AS
        SELECT
            adv_id,
            date,
            text,
            argMaxState(clicks, version) AS clicks,
            argMaxState(views, version) AS views,
            argMaxState(spend, version) AS spend
        FROM {ALLOWED_CH_DATABASE}.advkeyword
        GROUP BY adv_id, date, text
    """,
    f"DROP VIEW IF EXISTS {ALLOWED_CH_DATABASE}.cumulative_views",
    f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {ALLOWED_CH_DATABASE}.cumulative_views
        (
            `adv_id` UInt64,
            `text` String,
            `date` Date,
            `total_views` UInt64,
            `total_clicks` UInt64,
            `total_spend` Float64
        )
        ENGINE = SummingMergeTree
        ORDER BY (adv_id, text, date)
        SETTINGS index_granularity = 8192
        AS
        SELECT
            adv_id,
            text,
            date,
            views AS total_views,
            clicks AS total_clicks,
            spend AS total_spend
        FROM {ALLOWED_CH_DATABASE}.advkeyword
    """,
    f"DROP VIEW IF EXISTS {ALLOWED_CH_DATABASE}.mv_clusters_daily",
    f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {ALLOWED_CH_DATABASE}.mv_clusters_daily
        (
            `nmid` UInt64,
            `text` LowCardinality(String),
            `date` Date,
            `views_state` AggregateFunction(argMax, UInt32, DateTime),
            `clicks_state` AggregateFunction(argMax, UInt32, DateTime),
            `add_to_cart_state` AggregateFunction(argMax, UInt32, DateTime),
            `orders_state` AggregateFunction(argMax, UInt32, DateTime),
            `cpm_state` AggregateFunction(argMax, Float64, DateTime),
            `cpc_state` AggregateFunction(argMax, Float64, DateTime),
            `ts_state` AggregateFunction(max, DateTime)
        )
        ENGINE = AggregatingMergeTree
        ORDER BY (nmid, text, date)
        SETTINGS index_granularity = 8192
        AS
        SELECT nmid,
               norm_query AS text,
               date,
               argMaxState(views, timestamp) AS views_state,
               argMaxState(clicks, timestamp) AS clicks_state,
               argMaxState(add_to_cart, timestamp) AS add_to_cart_state,
               argMaxState(orders, timestamp) AS orders_state,
               argMaxState(cpm, timestamp) AS cpm_state,
               argMaxState(cpc, timestamp) AS cpc_state,
               maxState(timestamp) AS ts_state
        FROM {ALLOWED_CH_DATABASE}.clusters_adv_stats
        GROUP BY nmid, text, date
    """,
    f"DROP VIEW IF EXISTS {ALLOWED_CH_DATABASE}.mv_clusters_daily_agg",
    f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {ALLOWED_CH_DATABASE}.mv_clusters_daily_agg
        (
            `adv_id` UInt32,
            `nmid` UInt64,
            `norm_query` LowCardinality(String),
            `date` Date,
            `views_state` AggregateFunction(argMax, UInt32, DateTime),
            `clicks_state` AggregateFunction(argMax, UInt32, DateTime),
            `carts_state` AggregateFunction(argMax, UInt32, DateTime),
            `orders_state` AggregateFunction(argMax, UInt32, DateTime),
            `cpm_state` AggregateFunction(argMax, Float64, DateTime),
            `ts_state` AggregateFunction(max, DateTime)
        )
        ENGINE = AggregatingMergeTree()
        ORDER BY (adv_id, nmid, norm_query, date)
        SETTINGS index_granularity = 8192
        AS
        SELECT
            adv_id,
            nmid,
            norm_query,
            date,
            argMaxState(views, timestamp) AS views_state,
            argMaxState(clicks, timestamp) AS clicks_state,
            argMaxState(add_to_cart, timestamp) AS carts_state,
            argMaxState(orders, timestamp) AS orders_state,
            argMaxState(cpm, timestamp) AS cpm_state,
            maxState(timestamp) AS ts_state
        FROM {ALLOWED_CH_DATABASE}.clusters_adv_stats
        GROUP BY adv_id, nmid, norm_query, date
    """,
    f"DROP VIEW IF EXISTS {ALLOWED_CH_DATABASE}.mv_clusters_last_state",
    f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {ALLOWED_CH_DATABASE}.mv_clusters_last_state
        (
            `nmid` UInt64,
            `text` LowCardinality(String),
            `last_avg_pos_state` AggregateFunction(argMax, Float64, DateTime),
            `last_cpc_state` AggregateFunction(argMax, Float64, DateTime),
            `last_cpm_state` AggregateFunction(argMax, Float64, DateTime),
            `last_ts_state` AggregateFunction(max, DateTime)
        )
        ENGINE = AggregatingMergeTree
        ORDER BY (nmid, text)
        SETTINGS index_granularity = 8192
        AS
        SELECT nmid,
               norm_query AS text,
               argMaxState(avr_pos, timestamp) AS last_avg_pos_state,
               argMaxState(cpc, timestamp) AS last_cpc_state,
               argMaxState(cpm, timestamp) AS last_cpm_state,
               maxState(timestamp) AS last_ts_state
        FROM {ALLOWED_CH_DATABASE}.clusters_adv_stats
        GROUP BY nmid, norm_query
    """,
)


async def apply_clickhouse_session_ddl(client: Any) -> None:
    """Создать required tables/views один раз (session bootstrap)."""
    for statement in CH_SESSION_DDL_STATEMENTS:
        await client.command(statement)


async def reset_clickhouse_test_data(client: Any) -> None:
    """Очистить test-owned tables перед CH-dependent test body."""
    for table in CH_TEST_OWNED_TABLES:
        await client.command(f"TRUNCATE TABLE IF EXISTS {qualified_ch_table(table)}")
