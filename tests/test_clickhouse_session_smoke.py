"""Smoke: Guarded ClickHouse session against ``test_adv_bot_clickhouse`` only.

Destructive allowlist forbids unqualified CREATE/INSERT targets; all DDL/DML
must use ``test_adv_bot_clickhouse.<object>``.
"""

import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.utils.ch_semaphore import anti_ch_crash_semaphore

pytestmark = pytest.mark.destructive_local

_TEST_TABLE = "test_adv_bot_clickhouse.test_table"


@pytest.mark.asyncio
async def test_clickhouse_session_smoke(clickhouse_client: AsyncClient):
    """Проверяем, что async-клиент ClickHouse реально работает и БД отвечает"""
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query("SELECT 1")
    assert result.result_rows[0][0] == 1


@pytest.mark.asyncio
async def test_clickhouse_create_table(clickhouse_client: AsyncClient):
    """Qualified CREATE/INSERT/SELECT/DROP on ``test_adv_bot_clickhouse.test_table``."""
    await clickhouse_client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {_TEST_TABLE} (
            id UInt32,
            name String,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY id
        """
    )

    await clickhouse_client.insert(
        _TEST_TABLE,
        [[1, "test_name"], [2, "another_name"]],
        column_names=["id", "name"],
    )
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            f"SELECT COUNT(*) FROM {_TEST_TABLE}"
        )
    assert result.result_rows[0][0] == 2

    await clickhouse_client.command(f"DROP TABLE IF EXISTS {_TEST_TABLE}")



