from __future__ import annotations

from typing import Any
import logging

logger = logging.getLogger(__name__)

# NOTE: This module contains ClickHouse schema initialization logic.
# It should be called during application startup or upon first client acquisition
# to ensure required database and tables exist.


async def init_schema(client: Any, database: str = "default_db") -> None:
    # Create database if not exists
    try:
        await client.command(f"CREATE DATABASE IF NOT EXISTS {database}")
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных {database}: {e}")

    # advkeyword table (aggregated keyword stats per adv_id, text, date, version)
    await client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {database}.advkeyword (
            adv_id UInt64,
            text String,
            date Date,
            version UInt64,
            clicks UInt32,
            views UInt32,
            spend Float64
        )
        ENGINE = ReplacingMergeTree(version)
        ORDER BY (adv_id, text, date)
        """
    )

    # advkeyword indexes
    try:
        await client.command(
            f"""
            ALTER TABLE {database}.advkeyword
            ADD INDEX IF NOT EXISTS idx_advkeyword_text text TYPE bloom_filter GRANULARITY 64
            """
        )
        await client.command(
            f"ALTER TABLE {database}.advkeyword MATERIALIZE INDEX idx_advkeyword_text"
        )
    except Exception as e:
        logger.warning(f"Не удалось создать/материализовать индекс idx_advkeyword_text: {e}")

    try:
        await client.command(
            f"""
            ALTER TABLE {database}.advkeyword
            ADD INDEX IF NOT EXISTS idx_advkeyword_date date TYPE minmax GRANULARITY 1
            """
        )
        await client.command(
            f"ALTER TABLE {database}.advkeyword MATERIALIZE INDEX idx_advkeyword_date"
        )
    except Exception as e:
        logger.warning(f"Не удалось создать/материализовать индекс idx_advkeyword_date: {e}")

    # wbitemposition table (positions history)
    await client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {database}.wbitemposition (
            nmid UInt64,
            text String,
            promo_position Int32,
            base_position Int32,
            cpm Int32,
            adv_type Int32,
            timestamp DateTime,
            version UInt64
        )
        ENGINE = ReplacingMergeTree(version)
        ORDER BY (nmid, text, timestamp)
        """
    )

    # wbitemposition indexes
    try:
        await client.command(
            f"""
            ALTER TABLE {database}.wbitemposition
            ADD INDEX IF NOT EXISTS idx_wbitemposition_ts timestamp TYPE minmax GRANULARITY 1
            """
        )
        await client.command(
            f"ALTER TABLE {database}.wbitemposition MATERIALIZE INDEX idx_wbitemposition_ts"
        )
    except Exception as e:
        logger.warning(f"Не удалось создать/материализовать индекс idx_wbitemposition_ts: {e}")

    try:
        await client.command(
            f"""
            ALTER TABLE {database}.wbitemposition
            ADD INDEX IF NOT EXISTS idx_wbitemposition_text text TYPE bloom_filter GRANULARITY 64
            """
        )
        await client.command(
            f"ALTER TABLE {database}.wbitemposition MATERIALIZE INDEX idx_wbitemposition_text"
        )
    except Exception as e:
        logger.warning(f"Не удалось создать/материализовать индекс idx_wbitemposition_text: {e}")

    # wb_common_stat table (common stats per nmid/date)
    await client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {database}.wb_common_stat (
            nmid UInt64,
            date Date,
            open_card UInt32,
            add_to_cart UInt32,
            orders UInt32,
            orders_sum Float64,
            buy_outs UInt32,
            version Float64
        )
        ENGINE = ReplacingMergeTree(version)
        ORDER BY (nmid, date)
        """
    )

    # wb_common_stat indexes
    try:
        await client.command(
            f"""
            ALTER TABLE {database}.wb_common_stat
            ADD INDEX IF NOT EXISTS idx_wb_common_stat_date date TYPE minmax GRANULARITY 1
            """
        )
        await client.command(
            f"ALTER TABLE {database}.wb_common_stat MATERIALIZE INDEX idx_wb_common_stat_date"
        )
    except Exception as e:
        logger.warning(f"Не удалось создать/материализовать индекс idx_wb_common_stat_date: {e}")

    # full_adv_wb_stat table
    await client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {database}.full_adv_wb_stat (
            adv_id UInt64,
            date Date,
            views UInt32,
            clicks UInt32,
            spend Float64,
            added_to_cart UInt32,
            orders UInt32,
            sum_price_orders Float64,
            version Float64
        )
        ENGINE = ReplacingMergeTree(version)
        ORDER BY (adv_id, date)
        """
    )

    # full_adv_wb_stat indexes
    try:
        await client.command(
            f"""
            ALTER TABLE {database}.full_adv_wb_stat
            ADD INDEX IF NOT EXISTS idx_full_adv_wb_stat_date date TYPE minmax GRANULARITY 1
            """
        )
        await client.command(
            f"ALTER TABLE {database}.full_adv_wb_stat MATERIALIZE INDEX idx_full_adv_wb_stat_date"
        )
    except Exception as e:
        logger.warning(f"Не удалось создать/материализовать индекс idx_full_adv_wb_stat_date: {e}")

    # cumulative_views materialized view
    await client.command(
        f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {database}.cumulative_views
        ENGINE = SummingMergeTree()
        ORDER BY (adv_id, text, date)
        POPULATE
        AS SELECT
            adv_id,
            text,
            date,
            SUM(views) AS total_views,
            SUM(clicks) AS total_clicks,
            SUM(spend) AS total_spend
        FROM {database}.advkeyword
        GROUP BY adv_id, text, date;
        """
    )
