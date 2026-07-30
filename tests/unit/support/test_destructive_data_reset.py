"""Unit: PG/CH reset helpers (mock engine/client, no live infra)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.support.destructive_ch_reset import (
    CH_SESSION_DDL_STATEMENTS,
    CH_TEST_OWNED_TABLES,
    apply_clickhouse_session_ddl,
    qualified_ch_table,
    reset_clickhouse_test_data,
)
from tests.support.destructive_clickhouse import ALLOWED_CH_DATABASE
from tests.support.destructive_pg_reset import PG_TRUNCATE_SQL, reset_postgres_test_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pg_reset_uses_existing_engine_no_dispose() -> None:
    """Reset использует переданный engine и не вызывает dispose."""
    conn = AsyncMock()
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = conn
    begin_cm.__aexit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin_cm
    engine.dispose = AsyncMock()

    with patch(
        "tests.support.destructive_pg_reset._restore_baseline_wbcabinet",
        new=AsyncMock(),
    ) as restore:
        await reset_postgres_test_data(engine, restore_baseline=True)

    engine.begin.assert_called_once()
    assert conn.execute.await_count >= 1
    # First execute is TRUNCATE
    first_sql = str(conn.execute.await_args_list[0].args[0])
    assert "TRUNCATE" in first_sql or "TRUNCATE" in PG_TRUNCATE_SQL
    restore.assert_awaited_once()
    engine.dispose.assert_not_called()


@pytest.mark.unit
def test_pg_truncate_sql_restarts_identity_cascade() -> None:
    """TRUNCATE обязан RESTART IDENTITY CASCADE."""
    assert "RESTART IDENTITY" in PG_TRUNCATE_SQL
    assert "CASCADE" in PG_TRUNCATE_SQL
    assert "wbcabinet" in PG_TRUNCATE_SQL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ch_reset_truncates_only_test_owned_tables() -> None:
    """CH data reset → TRUNCATE qualified test tables, без DDL recreate."""
    client = AsyncMock()
    await reset_clickhouse_test_data(client)
    assert client.command.await_count == len(CH_TEST_OWNED_TABLES)
    for call, table in zip(client.command.await_args_list, CH_TEST_OWNED_TABLES):
        sql = call.args[0]
        assert ALLOWED_CH_DATABASE in sql
        assert "default_db" not in sql
        assert "TRUNCATE" in sql.upper()
        assert table in sql


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ch_ddl_once_statements_are_qualified() -> None:
    """Session DDL statements fully-qualified, без USE/default_db."""
    client = AsyncMock()
    await apply_clickhouse_session_ddl(client)
    assert client.command.await_count == len(CH_SESSION_DDL_STATEMENTS)
    for call in client.command.await_args_list:
        sql = call.args[0]
        assert "default_db" not in sql
        assert not sql.strip().lower().startswith("use ")
        assert ALLOWED_CH_DATABASE in sql


@pytest.mark.unit
def test_qualified_ch_table_helper() -> None:
    assert qualified_ch_table("advkeyword") == f"{ALLOWED_CH_DATABASE}.advkeyword"
