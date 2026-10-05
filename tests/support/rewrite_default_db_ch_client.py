"""Test-only: rewrite prod ``default_db.*`` → test CH DB before Guarded client.

Production SQL and insert targets must keep ``default_db`` (architecture).
Destructive tests forbid that name on GuardedClickHouseClient @ :8124.
This wrapper remaps qualifiers so Arrange/Act/Assert share the same
``test_adv_bot_clickhouse`` Guarded client without creating ``default_db``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any

import pytest

from tests.support.destructive_clickhouse import ALLOWED_CH_DATABASE

PROD_CH_DATABASE = "default_db"
TEST_CH_DATABASE = ALLOWED_CH_DATABASE


def rewrite_default_db_sql(sql: str) -> str:
    """Rewrite ``default_db.<object>`` qualifiers in a SQL string to the test DB.

    Args:
        sql: Production-shaped SQL that may reference ``default_db``.

    Returns:
        SQL with ``default_db.`` replaced by ``test_adv_bot_clickhouse.``.
    """
    return sql.replace(f"{PROD_CH_DATABASE}.", f"{TEST_CH_DATABASE}.")


def rewrite_default_db_table(table: str) -> str:
    """Rewrite a qualified insert table name from prod DB to the test DB.

    Args:
        table: Table argument as issued by production (often ``default_db.x``).

    Returns:
        Table name safe for GuardedClickHouseClient insert allowlist.
    """
    if table.startswith(f"{PROD_CH_DATABASE}."):
        return f"{TEST_CH_DATABASE}." + table[len(PROD_CH_DATABASE) + 1 :]
    if table == PROD_CH_DATABASE:
        return TEST_CH_DATABASE
    return table


class RewritingClickHouseClient:
    """Delegate to fixture Guarded client; rewrite ``default_db`` first.

    Production paths still emit ``default_db`` conceptually; this wrapper
    remaps SQL/table targets before the destructive allowlist or raw CH
    sees them.
    """

    def __init__(self, inner: Any) -> None:
        """Args:
            inner: GuardedClickHouseClient (or compatible) from the fixture.
        """
        self._inner = inner

    async def query(self, *args: Any, **kwargs: Any) -> Any:
        """Rewrite query SQL ``default_db.*``, then forward to inner client."""
        if args and isinstance(args[0], str):
            args = (rewrite_default_db_sql(args[0]), *args[1:])
        query = kwargs.get("query")
        if isinstance(query, str):
            kwargs = {**kwargs, "query": rewrite_default_db_sql(query)}
        return await self._inner.query(*args, **kwargs)

    async def command(self, *args: Any, **kwargs: Any) -> Any:
        """Rewrite command SQL ``default_db.*``, then forward to inner client."""
        if args and isinstance(args[0], str):
            args = (rewrite_default_db_sql(args[0]), *args[1:])
        for key in ("cmd", "query"):
            value = kwargs.get(key)
            if isinstance(value, str):
                kwargs = {**kwargs, key: rewrite_default_db_sql(value)}
                break
        return await self._inner.command(*args, **kwargs)

    async def insert(self, *args: Any, **kwargs: Any) -> Any:
        """Rewrite production insert table/database to the allowlisted test DB."""
        database = kwargs.get("database")
        if database == PROD_CH_DATABASE:
            kwargs = {**kwargs, "database": TEST_CH_DATABASE}
        if args:
            table, *rest = args
            if isinstance(table, str):
                table = rewrite_default_db_table(table)
            return await self._inner.insert(table, *rest, **kwargs)
        table = kwargs.get("table")
        if isinstance(table, str):
            kwargs = {**kwargs, "table": rewrite_default_db_table(table)}
        return await self._inner.insert(**kwargs)

    def close(self) -> Any:
        """Pass-through close to the inner client."""
        return self._inner.close()


def rewriting_clickhouse_client(inner: Any) -> RewritingClickHouseClient:
    """Build a rewrite wrapper around the fixture GuardedClickHouseClient.

    Args:
        inner: Fixture ``clickhouse_client`` (Guarded).

    Returns:
        Client that rewrites ``default_db`` before delegating.
    """
    return RewritingClickHouseClient(inner)


@asynccontextmanager
async def rewriting_get_clickhouse_client_cm(
    inner: Any,
) -> AsyncIterator[RewritingClickHouseClient]:
    """Async CM yielding a rewrite wrapper (drop-in for ``get_clickhouse_client``).

    Args:
        inner: Fixture ``clickhouse_client`` (Guarded).

    Yields:
        ``RewritingClickHouseClient`` over ``inner``.
    """
    yield RewritingClickHouseClient(inner)


def patch_get_clickhouse_client(
    monkeypatch: pytest.MonkeyPatch,
    modules: Iterable[Any],
    clickhouse_client: Any,
    *,
    attr: str = "get_clickhouse_client",
) -> RewritingClickHouseClient:
    """Monkeypatch module-level ``get_clickhouse_client`` to the rewrite CM.

    Production does ``async with get_clickhouse_client() as client``; each
    listed module's imported binding is replaced with an async context
    manager that yields the rewriting wrapper over the fixture client.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        modules: Modules that imported ``get_clickhouse_client`` (or alias).
        clickhouse_client: Fixture GuardedClickHouseClient.
        attr: Attribute name on each module (default ``get_clickhouse_client``;
            use ``get_client`` where production aliases the import).

    Returns:
        The shared ``RewritingClickHouseClient`` instance yielded by the CM.
    """
    redirected = RewritingClickHouseClient(clickhouse_client)

    @asynccontextmanager
    async def _fixture_clickhouse_client() -> AsyncIterator[Any]:
        yield redirected

    for module in modules:
        monkeypatch.setattr(module, attr, _fixture_clickhouse_client)
    return redirected
