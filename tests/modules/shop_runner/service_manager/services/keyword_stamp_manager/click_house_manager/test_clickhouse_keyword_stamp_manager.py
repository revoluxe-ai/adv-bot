"""Integration: keyword stamp CH manager on Guarded test DB (no CREATE DATABASE).

Production inserts/queries use ``default_db.*``; tests rewrite to
``test_adv_bot_clickhouse.*`` before the destructive guard. Database
CREATE/DROP is forbidden — only qualified TABLE DDL/DML.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from clickhouse_connect.driver import AsyncClient

from app.core.mp.wb.dto import KeywordPosition
import app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager.click_house_manager as keyword_stamp_ch_module
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager import (
    ClickHouseKeywordJamStatManager,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from tests.factories import KeywordStatFromJamFactory
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client

pytestmark = pytest.mark.destructive_local


@pytest.mark.asyncio
async def test_update_positions_inserts_dat_into_clickhouse(
    clickhouse_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CREATE/TRUNCATE TABLE → update_positions via rewrite → assert row count/fields."""
    table_name = "test_adv_bot_clickhouse.keyword_position_from_api"
    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {table_name}")
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name}
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
            ORDER BY (nmid, date)
            SETTINGS index_granularity = 8192;
    """
    _ = await clickhouse_client.command(create_table_sql)

    num_positions = 3
    test_positions: list[KeywordPosition] = KeywordStatFromJamFactory.build_batch(num_positions)

    patch_get_clickhouse_client(
        monkeypatch, [keyword_stamp_ch_module], clickhouse_client
    )
    await ClickHouseKeywordJamStatManager.update_positions(test_positions)
    async with anti_ch_crash_semaphore:
        count_result = await clickhouse_client.query(f"SELECT COUNT(*) FROM {table_name}")
    assert count_result.result_rows[0][0] == num_positions
    async with anti_ch_crash_semaphore:
        select_result = await clickhouse_client.query(
            f"SELECT nmid, text, avr_position, total_views, orders, date FROM {table_name} ORDER BY nmid"
        )
    actual_rows = select_result.result_rows
    sorted_test_positions = sorted(test_positions, key=lambda p: p.nmid)

    for i, actual_row in enumerate(actual_rows):
        expected_position: KeywordPosition = sorted_test_positions[i]
        assert actual_row[0] == expected_position.nmid
        assert actual_row[1] == expected_position.text
        assert actual_row[2] == pytest.approx(expected_position.average_position, rel=1e-3)
        assert actual_row[3] == expected_position.total_views_avr_for_day
        assert actual_row[4] == expected_position.orders
        assert actual_row[5] == date(
            expected_position.date.year,
            expected_position.date.month,
            expected_position.date.day,
        )

    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {table_name}")


@pytest.mark.asyncio
async def test_get_last_positions_returns_total_orders(
    clickhouse_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seed stamp/positions tables → get_last_positions via rewrite → assert aggregates."""
    stamp_table = "test_adv_bot_clickhouse.keyword_stamp"
    positions_table = "test_adv_bot_clickhouse.keyword_position_from_api"

    for table in (stamp_table, positions_table):
        _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {table}")

    stamp_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {stamp_table}
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
    _ = await clickhouse_client.command(stamp_table_sql)

    positions_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {positions_table}
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
            ORDER BY (nmid, date)
            SETTINGS index_granularity = 8192;
    """
    _ = await clickhouse_client.command(positions_table_sql)

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    base_ts = datetime.combine(today, datetime.min.time())
    ts_10 = (base_ts + timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")
    ts_11 = (base_ts + timedelta(hours=11)).strftime("%Y-%m-%d %H:%M:%S")
    ts_12 = (base_ts + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")

    stamp_insert_sql = f"""
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
        ('shop', 100, 1, 'keyword', 10.0, 4, 100, 50, '{today_str}', '{ts_10}', 1),
        ('shop', 100, 1, 'keyword', 8.0, 5, 130, 55, '{today_str}', '{ts_11}', 2),
        ('shop', 100, 1, 'other', 12.0, 3, 90, 40, '{today_str}', '{ts_10}', 3),
        ('shop', 100, 1, 'other', 11.0, 4, 120, 45, '{today_str}', '{ts_12}', 4)
    """
    await clickhouse_client.command(stamp_insert_sql)

    positions_insert_sql = f"""
        INSERT INTO {positions_table} (
            nmid,
            text,
            avr_position,
            total_views,
            orders,
            date,
            version
        ) VALUES
        (1, 'keyword', 7.0, 70, 3, '{yesterday_str}', 1),
        (1, 'other', 10.0, 60, 2, '{yesterday_str}', 2),
        (1, 'other', 10.0, 60, 5, '{yesterday_str}', 3)
    """
    await clickhouse_client.command(positions_insert_sql)

    adv_setting = SimpleNamespace(nmids=[1], adv_id=100, type=8)

    patch_get_clickhouse_client(
        monkeypatch, [keyword_stamp_ch_module], clickhouse_client
    )
    positions = await ClickHouseKeywordJamStatManager.get_last_positions(adv_setting)

    assert len(positions) == 2
    totals = {pos.keyword_text: pos.total_orders for pos in positions}
    views = {pos.keyword_text: pos.total_views for pos in positions}

    # Текущая реализация агрегирует только свежие версии из таблицы keyword_stamp.
    assert totals["keyword"] == 5
    assert totals["other"] == 9
    assert views["keyword"] == 130
    assert views["other"] == 180

    for table in (stamp_table, positions_table):
        _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {table}")
