"""Unit: fail-closed validator для destructive ClickHouse test endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.support.destructive_clickhouse import (
    ALLOWED_CH_DATABASE,
    ALLOWED_CH_HTTP_PORT,
    DestructiveTestClickHouseError,
    create_validated_async_clickhouse_client,
    validate_destructive_clickhouse_endpoint,
    validate_destructive_clickhouse_from_environ,
)

_OPT_IN = {"ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE": "1"}


@pytest.mark.unit
def test_valid_localhost_with_opt_in() -> None:
    """Allowlist: 127.0.0.1:8124/test_adv_bot_clickhouse + opt-in."""
    got = validate_destructive_clickhouse_endpoint(
        host="127.0.0.1",
        port=ALLOWED_CH_HTTP_PORT,
        database=ALLOWED_CH_DATABASE,
        environ=_OPT_IN,
    )
    assert got.host == "127.0.0.1"
    assert got.port == ALLOWED_CH_HTTP_PORT
    assert got.database == ALLOWED_CH_DATABASE
    assert got.database == "test_adv_bot_clickhouse"
    assert "password" not in got.render_redacted().lower() or "***" in got.render_redacted()


@pytest.mark.unit
def test_default_db_forbidden() -> None:
    """Prod SQL prefix default_db запрещён для destructive tests."""
    with pytest.raises(DestructiveTestClickHouseError, match="forbidden"):
        validate_destructive_clickhouse_endpoint(
            host="127.0.0.1",
            port=ALLOWED_CH_HTTP_PORT,
            database="default_db",
            environ=_OPT_IN,
        )


@pytest.mark.unit
def test_missing_opt_in_refused() -> None:
    with pytest.raises(DestructiveTestClickHouseError, match="opt-in"):
        validate_destructive_clickhouse_endpoint(
            host="127.0.0.1",
            port=ALLOWED_CH_HTTP_PORT,
            database=ALLOWED_CH_DATABASE,
            environ={},
        )


@pytest.mark.unit
def test_empty_host_refused() -> None:
    with pytest.raises(DestructiveTestClickHouseError, match="host is empty"):
        validate_destructive_clickhouse_endpoint(
            host="",
            port=ALLOWED_CH_HTTP_PORT,
            database=ALLOWED_CH_DATABASE,
            environ=_OPT_IN,
        )


@pytest.mark.unit
def test_prod_host_refused() -> None:
    with pytest.raises(DestructiveTestClickHouseError, match="not allowlisted"):
        validate_destructive_clickhouse_endpoint(
            host="clickhouse.prod.example",
            port=ALLOWED_CH_HTTP_PORT,
            database=ALLOWED_CH_DATABASE,
            environ=_OPT_IN,
        )


@pytest.mark.unit
def test_wrong_port_refused() -> None:
    with pytest.raises(DestructiveTestClickHouseError, match="not the test HTTP port"):
        validate_destructive_clickhouse_endpoint(
            host="127.0.0.1",
            port=8123,
            database=ALLOWED_CH_DATABASE,
            environ=_OPT_IN,
        )


@pytest.mark.unit
def test_forbidden_database_refused() -> None:
    with pytest.raises(DestructiveTestClickHouseError):
        validate_destructive_clickhouse_endpoint(
            host="127.0.0.1",
            port=ALLOWED_CH_HTTP_PORT,
            database="production",
            environ=_OPT_IN,
        )


@pytest.mark.unit
def test_from_environ_reads_host_port() -> None:
    env = {
        **_OPT_IN,
        "CLICK_HOUSE_HOST": "localhost",
        "CLICKHOUSE_PORT": str(ALLOWED_CH_HTTP_PORT),
        "CLICK_HOUSE_USER": "u",
    }
    got = validate_destructive_clickhouse_from_environ(environ=env)
    assert got.host == "localhost"
    assert got.port == ALLOWED_CH_HTTP_PORT
    assert got.database == ALLOWED_CH_DATABASE


@pytest.mark.unit
def test_tunnels_refuse_before_client() -> None:
    with pytest.raises(DestructiveTestClickHouseError, match="DEV_TUNNELS"):
        validate_destructive_clickhouse_endpoint(
            host="127.0.0.1",
            port=ALLOWED_CH_HTTP_PORT,
            database=ALLOWED_CH_DATABASE,
            environ={**_OPT_IN, "DEV_TUNNELS_ENABLED": "true"},
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_async_client_not_called_when_invalid() -> None:
    """Factory get_async_client не вызывается при fail validation."""
    factory = AsyncMock()
    with pytest.raises(DestructiveTestClickHouseError):
        await create_validated_async_clickhouse_client(
            host="203.0.113.10",
            port=ALLOWED_CH_HTTP_PORT,
            database=ALLOWED_CH_DATABASE,
            username="u",
            password="secret",
            get_async_client_fn=factory,
            environ=_OPT_IN,
        )
    factory.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_async_client_not_called_without_opt_in() -> None:
    factory = AsyncMock()
    with pytest.raises(DestructiveTestClickHouseError, match="opt-in"):
        await create_validated_async_clickhouse_client(
            host="127.0.0.1",
            port=ALLOWED_CH_HTTP_PORT,
            database=ALLOWED_CH_DATABASE,
            username="u",
            password="secret",
            get_async_client_fn=factory,
            environ={},
        )
    factory.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_async_client_called_only_after_valid() -> None:
    factory = AsyncMock(return_value=MagicMock())
    await create_validated_async_clickhouse_client(
        host="127.0.0.1",
        port=ALLOWED_CH_HTTP_PORT,
        database=ALLOWED_CH_DATABASE,
        username="u",
        password="secret",
        get_async_client_fn=factory,
        environ=_OPT_IN,
        wrap_sql_guard=False,
    )
    factory.assert_awaited_once()
    kwargs = factory.await_args.kwargs
    assert kwargs["database"] == "test_adv_bot_clickhouse"
    assert kwargs["host"] == "127.0.0.1"


@pytest.mark.unit
def test_sql_guard_rejects_default_db() -> None:
    from tests.support.destructive_clickhouse import assert_destructive_clickhouse_sql_allowed

    with pytest.raises(DestructiveTestClickHouseError, match="default_db"):
        assert_destructive_clickhouse_sql_allowed(
            "TRUNCATE TABLE default_db.plan_fact_stats"
        )


@pytest.mark.unit
def test_sql_guard_rejects_foreign_db_ddl() -> None:
    from tests.support.destructive_clickhouse import assert_destructive_clickhouse_sql_allowed

    with pytest.raises(DestructiveTestClickHouseError, match="test_adv_bot_clickhouse"):
        assert_destructive_clickhouse_sql_allowed(
            "DROP TABLE IF EXISTS production.plan_fact_stats"
        )


@pytest.mark.unit
def test_sql_guard_allows_qualified_test_db() -> None:
    from tests.support.destructive_clickhouse import assert_destructive_clickhouse_sql_allowed

    assert_destructive_clickhouse_sql_allowed(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_guarded_client_command_blocks_before_underlying() -> None:
    from tests.support.destructive_clickhouse import GuardedClickHouseClient

    underlying = MagicMock()
    underlying.command = AsyncMock()
    guarded = GuardedClickHouseClient(underlying)
    with pytest.raises(DestructiveTestClickHouseError, match="default_db"):
        await guarded.command("SELECT * FROM default_db.x")
    underlying.command.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_guarded_client_insert_blocks_before_underlying() -> None:
    from tests.support.destructive_clickhouse import GuardedClickHouseClient

    underlying = MagicMock()
    underlying.insert = AsyncMock()
    guarded = GuardedClickHouseClient(underlying)
    with pytest.raises(DestructiveTestClickHouseError, match="default_db"):
        await guarded.insert("default_db.plan_fact_stats", [[1]], ["id"])
    underlying.insert.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sql",
    [
        "USE default_db",
        "DROP TABLE table_name",
        "DROP TABLE `default_db`.`table_name`",
        'TRUNCATE TABLE "default_db"."table_name"',
        "CREATE DATABASE default_db",
        "SELECT 1; DROP TABLE test_adv_bot_clickhouse.t",
    ],
)
async def test_guarded_client_command_blocks_policy_bypasses(sql: str) -> None:
    """Wrapper должен блокировать SQL bypass-формы до вызова underlying."""
    from tests.support.destructive_clickhouse import GuardedClickHouseClient

    underlying = MagicMock()
    underlying.command = AsyncMock()
    guarded = GuardedClickHouseClient(underlying)

    with pytest.raises(DestructiveTestClickHouseError):
        await guarded.command(sql)
    underlying.command.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_guarded_client_query_blocks_multistatement_before_underlying() -> None:
    """query тоже проходит через SQL policy и не вызывает underlying на deny."""
    from tests.support.destructive_clickhouse import GuardedClickHouseClient

    underlying = MagicMock()
    underlying.query = AsyncMock()
    guarded = GuardedClickHouseClient(underlying)

    with pytest.raises(DestructiveTestClickHouseError, match="multi-statement"):
        await guarded.query("SELECT 1; SELECT 2")
    underlying.query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_guarded_client_insert_requires_qualified_test_db() -> None:
    """insert с unqualified table запрещён до underlying.insert."""
    from tests.support.destructive_clickhouse import GuardedClickHouseClient

    underlying = MagicMock()
    underlying.insert = AsyncMock()
    guarded = GuardedClickHouseClient(underlying)

    with pytest.raises(DestructiveTestClickHouseError, match="fully-qualified"):
        await guarded.insert("plan_fact_stats", [[1]], ["id"])
    underlying.insert.assert_not_called()


@pytest.mark.unit
def test_guarded_client_raw_access_is_not_exposed() -> None:
    """Raw underlying client недоступен через _client/любой другой атрибут."""
    from tests.support.destructive_clickhouse import GuardedClickHouseClient

    guarded = GuardedClickHouseClient(MagicMock())
    with pytest.raises(AttributeError, match="Allowed API"):
        _ = guarded._client  # type: ignore[attr-defined]
    with pytest.raises(AttributeError, match="Allowed API"):
        _ = guarded.any_unknown_attr  # type: ignore[attr-defined]
