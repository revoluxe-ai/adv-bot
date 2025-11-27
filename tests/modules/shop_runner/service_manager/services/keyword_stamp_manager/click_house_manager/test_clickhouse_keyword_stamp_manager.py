from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from clickhouse_connect.driver import AsyncClient

from app.core.mp.wb.dto import KeywordPosition
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager import (
    ClickHouseKeywordStampManager,
)
from app.utils.click_house.client import get_clickhouse_client
from tests.factories import KeywordPositionFactory


@pytest.mark.asyncio
async def test_update_positions_inserts_dat_into_clickhouse(clickhouse_client: AsyncClient) -> None:
    _ = await clickhouse_client.command("CREATE DATABASE IF NOT EXISTS default_db")

    table_name = "default_db.keyword_position_from_api"
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
    test_positions: list[KeywordPosition] = KeywordPositionFactory.build_batch(num_positions)

    with patch(
        "app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager.click_house_manager.get_clickhouse_client"
    ) as get_clickhouse_client_mock:
        cm = AsyncMock()
        cm.__aenter__.return_value = clickhouse_client
        cm.__aexit__.return_value = None

        get_clickhouse_client_mock.return_value = cm

        await ClickHouseKeywordStampManager.update_positions(test_positions)

    count_result = await clickhouse_client.query(f"SELECT COUNT(*) FROM {table_name}")
    assert count_result.result_rows[0][0] == num_positions

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
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

import pytest
from clickhouse_connect.driver import AsyncClient

from app.core.mp.wb.dto import KeywordPosition
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager import ClickHouseKeywordStampManager
from tests.factories import KeywordPositionFactory


@pytest.mark.asyncio
async def test_update_positions_inserts_dat_into_clickhouse(clickhouse_client: AsyncClient) -> None:
    _ = await clickhouse_client.command("CREATE DATABASE IF NOT EXISTS default_db")

    table_name = "default_db.keyword_position_from_api"
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
    test_positions: list[KeywordPosition] = KeywordPositionFactory.build_batch(num_positions)

    with patch(
        "app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager.click_house_manager.get_clickhouse_client"
    ) as get_clickhouse_client_mock:
        cm = AsyncMock()
        cm.__aenter__.return_value = clickhouse_client
        cm.__aexit__.return_value = None

        get_clickhouse_client_mock.return_value = cm

        await ClickHouseKeywordStampManager.update_positions(test_positions)

    count_result = await clickhouse_client.query(f"SELECT COUNT(*) FROM {table_name}")
    assert count_result.result_rows[0][0] == num_positions

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
async def test_get_last_positions_returns_total_orders(clickhouse_client: AsyncClient) -> None:
    _ = await clickhouse_client.command("CREATE DATABASE IF NOT EXISTS default_db")
    table_name = "default_db.keyword_stamp"
    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {table_name}")
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name}
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
    _ = await clickhouse_client.command(create_table_sql)

    insert_sql = f"""
        INSERT INTO {table_name} (
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
        ('shop', 100, 1, 'keyword', 10.0, 2, 100, 50, '2025-11-01', '2025-11-01 10:00:00', 1),
        ('shop', 100, 1, 'keyword', 9.0, 5, 120, 50, '2025-11-01', '2025-11-01 11:00:00', 2),
        ('shop', 100, 1, 'keyword', 8.0, 1, 130, 50, '2025-11-02', '2025-11-02 13:00:00', 1),
        ('shop', 100, 1, 'other', 12.0, 4, 80, 40, '2025-11-01', '2025-11-01 09:00:00', 1)
    """

    await clickhouse_client.command(insert_sql)

    adv_setting = SimpleNamespace(nmids=[1], adv_id=100, type=8)
    positions = await ClickHouseKeywordStampManager.get_last_positions(adv_setting)

    assert len(positions) == 2
    total_orders_by_keyword = {
        position.keyword_text: position.total_orders for position in positions
    }
    assert total_orders_by_keyword["keyword"] == 8
    assert total_orders_by_keyword["other"] == 4

    _ = await clickhouse_client.command(f"DROP TABLE IF EXISTS {table_name}")
