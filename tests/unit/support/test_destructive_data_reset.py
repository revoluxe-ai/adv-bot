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
from tests.support.destructive_pg_reset import (
    PG_RESET_ADVISORY_LOCK_KEY,
    PG_TERMINATE_OTHER_BACKENDS_SQL,
    PG_TRUNCATE_SQL,
    init_postgres_schema_and_seed,
    is_pg_deadlock_error,
    reset_postgres_test_data,
)


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
    assert conn.execute.await_count >= 2
    # First execute is advisory lock; second is TRUNCATE
    first_sql = str(conn.execute.await_args_list[0].args[0])
    second_sql = str(conn.execute.await_args_list[1].args[0])
    assert "pg_advisory_xact_lock" in first_sql
    assert "TRUNCATE" in second_sql or "TRUNCATE" in PG_TRUNCATE_SQL
    restore.assert_awaited_once()
    engine.dispose.assert_not_called()


@pytest.mark.unit
def test_pg_truncate_sql_restarts_identity_cascade() -> None:
    """TRUNCATE обязан RESTART IDENTITY CASCADE."""
    assert "RESTART IDENTITY" in PG_TRUNCATE_SQL
    assert "CASCADE" in PG_TRUNCATE_SQL
    assert "wbcabinet" in PG_TRUNCATE_SQL


@pytest.mark.unit
def test_pg_terminate_other_backends_sql_targets_client_backends() -> None:
    """Terminate SQL не трогает свой pid и только client backend."""
    assert "pg_terminate_backend" in PG_TERMINATE_OTHER_BACKENDS_SQL
    assert "pg_backend_pid()" in PG_TERMINATE_OTHER_BACKENDS_SQL
    assert "client backend" in PG_TERMINATE_OTHER_BACKENDS_SQL
    assert "current_database()" in PG_TERMINATE_OTHER_BACKENDS_SQL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pg_schema_init_terminates_backends_before_drop() -> None:
    """Bootstrap обязан terminate + timeouts до DROP SCHEMA (анти-hang)."""
    conn = AsyncMock()
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = conn
    begin_cm.__aexit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin_cm
    conn.run_sync = AsyncMock(return_value=None)

    with patch(
        "tests.support.destructive_pg_reset._restore_baseline_wbcabinet",
        new=AsyncMock(),
    ):
        await init_postgres_schema_and_seed(engine)

    sqls = [str(call.args[0]) for call in conn.execute.await_args_list]
    term_idx = next(i for i, s in enumerate(sqls) if "pg_terminate_backend" in s)
    drop_idx = next(i for i, s in enumerate(sqls) if "DROP SCHEMA" in s)
    assert any("lock_timeout" in s for s in sqls[:term_idx])
    assert any("statement_timeout" in s for s in sqls[:term_idx])
    assert term_idx < drop_idx
    conn.run_sync.assert_awaited()


@pytest.mark.unit
def test_is_pg_deadlock_error_detects_asyncpg_and_sqlstate() -> None:
    """Классификатор deadlock покрывает имя исключения, sqlstate и текст."""

    class DeadlockDetectedError(Exception):
        """Minimal asyncpg-shaped stand-in."""

        sqlstate = "40P01"

    assert is_pg_deadlock_error(DeadlockDetectedError("deadlock detected"))

    class Wrapped(Exception):
        """SQLAlchemy-shaped wrapper with .orig."""

        def __init__(self) -> None:
            super().__init__("wrapper")
            self.orig = DeadlockDetectedError("deadlock detected")

    assert is_pg_deadlock_error(Wrapped())
    assert is_pg_deadlock_error(RuntimeError("other")) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pg_reset_retries_deadlock_then_succeeds() -> None:
    """DeadlockDetectedError на TRUNCATE → bounded retry, затем success."""

    class DeadlockDetectedError(Exception):
        sqlstate = "40P01"

    conn = AsyncMock()
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = conn
    begin_cm.__aexit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin_cm

    call_count = {"n": 0}

    async def _execute(sql: object, *args: object, **kwargs: object) -> MagicMock:
        sql_text = str(sql)
        if "pg_advisory_xact_lock" in sql_text:
            return MagicMock()
        if "TRUNCATE" in sql_text:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise DeadlockDetectedError("deadlock detected")
            return MagicMock()
        return MagicMock()

    conn.execute.side_effect = _execute
    sleeps: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    with patch(
        "tests.support.destructive_pg_reset._restore_baseline_wbcabinet",
        new=AsyncMock(),
    ):
        await reset_postgres_test_data(
            engine,
            restore_baseline=True,
            max_attempts=3,
            sleep_fn=_fake_sleep,
        )

    assert call_count["n"] == 2
    assert engine.begin.call_count == 2
    assert sleeps == [0.05]
    assert PG_RESET_ADVISORY_LOCK_KEY == 874_512_903


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pg_reset_raises_after_deadlock_budget_exhausted() -> None:
    """После исчерпания deadlock budget — пробрасываем последнюю ошибку."""

    class DeadlockDetectedError(Exception):
        sqlstate = "40P01"

    conn = AsyncMock()
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = conn
    begin_cm.__aexit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin_cm

    async def _always_deadlock(sql: object, *args: object, **kwargs: object) -> MagicMock:
        if "TRUNCATE" in str(sql):
            raise DeadlockDetectedError("deadlock detected")
        return MagicMock()

    conn.execute.side_effect = _always_deadlock

    async def _fake_sleep(_delay: float) -> None:
        return None

    with (
        patch(
            "tests.support.destructive_pg_reset._restore_baseline_wbcabinet",
            new=AsyncMock(),
        ),
        pytest.raises(DeadlockDetectedError),
    ):
        await reset_postgres_test_data(
            engine,
            restore_baseline=True,
            max_attempts=2,
            sleep_fn=_fake_sleep,
        )

    assert engine.begin.call_count == 2


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
