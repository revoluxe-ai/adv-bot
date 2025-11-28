import datetime

import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.modules.wb_adv_updater.total_orders_manager import TotalOrdersManager


@pytest.mark.asyncio
async def test_get_total_orders_combines_tables(clickhouse_client: AsyncClient) -> None:
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    day_before = today - datetime.timedelta(days=2)

    _ = await clickhouse_client.command("CREATE DATABASE IF NOT EXISTS default_db")

    stamp_table = "default_db.keyword_stamp"
    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {stamp_table}")
    await clickhouse_client.command(
        r"""
        CREATE TABLE IF NOT EXISTS default_db.keyword_stamp
        (
            shop_id      LowCardinality(String),
            adv_id       Int32,
            nmid         UInt32,
            text         String,
            avr_position Float32,
            orders       UInt32,
            total_views  UInt32,
            current_cpm  Int32,
            date         Date,
            timestamp    DateTime('Europe/Moscow'),
            version      UInt64
        )
        ENGINE = MergeTree
        PARTITION BY toYYYYMM(date)
        ORDER BY (shop_id, adv_id, nmid, text, date, timestamp)
        SETTINGS index_granularity = 8192;
    """
    )

    history_table = "default_db.keyword_position_from_api"
    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {history_table}")
    await clickhouse_client.command(
        r"""
        CREATE TABLE IF NOT EXISTS default_db.keyword_position_from_api
        (
            nmid         Int32,
            text         String,
            avr_position Float32,
            total_views  Int32,
            orders       Int32,
            date         Date,
            version      UInt64
        )
        ENGINE = ReplacingMergeTree(version)
            ORDER BY (nmid, text, date)
            SETTINGS index_granularity = 8192;
    """
    )

    await clickhouse_client.command(
        rf"""
        INSERT INTO {history_table} (
            nmid,
            text,
            avr_position,
            total_views,
            orders,
            date,
            version
        ) VALUES
        (1, 'keyword', 10, 100, 3, '{yesterday}', 1),
        (1, 'keyword', 11, 110, 5, '{yesterday}', 2),
        (1, 'keyword', 12, 120, 4, '{day_before}', 1),
        (1, 'other', 15, 80, 2, '{yesterday}', 1)
    """
    )

    await clickhouse_client.command(
        rf"""
        INSERT INTO {stamp_table} (
            shop_id,
            adv_id,
            nmid,
            text,
            avr_position,
            orders,
            total_views,
            current_cpm,
            date,
            timestamp,
            version
        ) VALUES
        ('shop', 100, 1, 'keyword', 9.5, 6, 130, 40, '{today}', '{today} 10:00:00', 1),
        ('shop', 100, 1, 'keyword', 9.0, 10, 150, 45, '{today}', '{today} 11:00:00', 2)
    """
    )

    orders_map = await TotalOrdersManager.get_total_orders(
        nmid=1,
        keywords_texts=["keyword", "other", "missing"],
    )

    assert orders_map["keyword"] == 19  # 5 (yesterday) + 4 (day_before) + 10 (today)
    assert orders_map["other"] == 2
    assert orders_map["missing"] == 0


@pytest.mark.asyncio
async def test_get_total_stats_combines_orders_and_views(clickhouse_client: AsyncClient) -> None:
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    day_before = today - datetime.timedelta(days=2)

    _ = await clickhouse_client.command("CREATE DATABASE IF NOT EXISTS default_db")

    stamp_table = "default_db.keyword_stamp"
    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {stamp_table}")
    await clickhouse_client.command(
        r"""
        CREATE TABLE IF NOT EXISTS default_db.keyword_stamp
        (
            shop_id      LowCardinality(String),
            adv_id       Int32,
            nmid         UInt32,
            text         String,
            avr_position Float32,
            orders       UInt32,
            total_views  UInt32,
            current_cpm  Int32,
            date         Date,
            timestamp    DateTime('Europe/Moscow'),
            version      UInt64
        )
        ENGINE = MergeTree
        PARTITION BY toYYYYMM(date)
        ORDER BY (shop_id, adv_id, nmid, text, date, timestamp)
        SETTINGS index_granularity = 8192;
    """
    )

    history_table = "default_db.keyword_position_from_api"
    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {history_table}")
    await clickhouse_client.command(
        r"""
        CREATE TABLE IF NOT EXISTS default_db.keyword_position_from_api
        (
            nmid         Int32,
            text         String,
            avr_position Float32,
            total_views  Int32,
            orders       Int32,
            date         Date,
            version      UInt64
        )
        ENGINE = ReplacingMergeTree(version)
            ORDER BY (nmid, text, date)
            SETTINGS index_granularity = 8192;
    """
    )

    await clickhouse_client.command(
        rf"""
        INSERT INTO {history_table} (
            nmid,
            text,
            avr_position,
            total_views,
            orders,
            date,
            version
        ) VALUES
        (1, 'keyword', 10, 100, 3, '{yesterday}', 1),
        (1, 'keyword', 11, 110, 5, '{yesterday}', 2),
        (1, 'keyword', 12, 120, 4, '{day_before}', 1),
        (1, 'other', 15, 80, 2, '{yesterday}', 1)
    """
    )

    await clickhouse_client.command(
        rf"""
        INSERT INTO {stamp_table} (
            shop_id,
            adv_id,
            nmid,
            text,
            avr_position,
            orders,
            total_views,
            current_cpm,
            date,
            timestamp,
            version
        ) VALUES
        ('shop', 100, 1, 'keyword', 9.5, 6, 130, 40, '{today}', '{today} 10:00:00', 1),
        ('shop', 100, 1, 'keyword', 9.0, 10, 150, 45, '{today}', '{today} 11:00:00', 2)
    """
    )

    stats_map = await TotalOrdersManager.get_total_stats(
        nmid=1,
    )

    # keyword: orders = 5 (yesterday) + 4 (day_before) + 10 (today) = 19
    # keyword: views = 150 (ТОЛЬКО за сегодня из keyword_stamp)
    assert stats_map["keyword"] == (19, 150)
    
    # other: only historical data, no data for today
    # orders = 2 (historical), views = 0 (no today data)
    assert stats_map["other"] == (2, 0)
    
    # missing: not in database, so not in result
    assert "missing" not in stats_map


