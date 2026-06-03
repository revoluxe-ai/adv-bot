"""Единые лимиты запросов PG/CH из env."""

from __future__ import annotations

import pytest

from app.utils import resource_limits


@pytest.mark.unit
def test_postgres_query_concurrency_prefers_new_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_QUERY_CONCURRENCY", "12")
    monkeypatch.setenv("COUNT_SEMAPHORE_TO_POSTGRES", "99")
    assert resource_limits.postgres_query_concurrency() == 12


@pytest.mark.unit
def test_clickhouse_query_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLICKHOUSE_QUERY_CONCURRENCY", "3")
    assert resource_limits.clickhouse_query_concurrency() == 3
