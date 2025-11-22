from datetime import date
from unittest.mock import patch, AsyncMock

import pytest
from clickhouse_connect.driver import AsyncClient

from app.core.mp.wb.dto import KeywordPosition
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager import \
    ClickHouseKeywordStampManager
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

    with patch('app.modules.shop_runner.'
               'service_manager.services.keyword_stamp_manager.'
               'click_house_manager.click_house_manager.get_clickhouse_client') as \
             get_clickhouse_client_mock:
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
