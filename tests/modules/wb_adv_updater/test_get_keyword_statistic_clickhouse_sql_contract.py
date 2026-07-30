"""SQL-contract: qualification ``default_db`` в issued SQL keyword-статистики.

Capability: ``clickhouse-query-database-qualification``.
Доказывает, что ``get_keyword_statistic_clickhouse`` передаёт в CH client
квалифицированное имя MV, а не полагается только на session database.
Полный mock самой функции запрещён (SQL_REWRITE_MOCKED_AWAY).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.wb_adv_updater import data_manager


class _CapturingQueryClient:
    """Fake CH client: сохраняет issued SQL, возвращает пустые агрегаты."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def query(self, query: str, *args: object, **kwargs: object) -> SimpleNamespace:
        """Захватывает текст SQL, который ушёл бы в ClickHouse."""
        self.queries.append(query)
        return SimpleNamespace(result_rows=[(0, 0, 0.0)])


@pytest.mark.asyncio
async def test_get_keyword_statistic_clickhouse_sql_qualifies_default_db_mv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec ``clickhouse-query-database-qualification``: issued SQL MUST
    содержать ``default_db.mv_clusters_daily_agg``.

    Перехватываем ``client.query`` (causal boundary — текст SQL), не мокаем
    ``get_keyword_statistic_clickhouse`` целиком. Semaphore подменяем узко,
    чтобы unit не зависел от глобального CH throttle.
    """
    client = _CapturingQueryClient()

    class _DummySemaphore:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *args: object) -> bool:
            return False

    monkeypatch.setattr(
        data_manager, "anti_ch_crash_semaphore", _DummySemaphore()
    )

    clicks, views, spend = await data_manager.get_keyword_statistic_clickhouse(
        client,
        text="тест",
        adv_ids={101, 202},
        pass_days=7,
    )

    assert clicks == 0 and views == 0 and spend == 0.0
    assert len(client.queries) == 1
    sql = client.queries[0]
    assert "default_db.mv_clusters_daily_agg" in sql
    # Unqualified form must not be the addressing form for the MV.
    assert "FROM mv_clusters_daily_agg" not in sql
    assert "FROM default_db.mv_clusters_daily_agg" in sql


@pytest.mark.asyncio
async def test_get_keyword_statistic_clickhouse_empty_adv_ids_skips_query() -> None:
    """Пустой ``adv_ids`` — ранний return без CH round-trip (smoke соседний)."""
    client = _CapturingQueryClient()
    client.query = AsyncMock(side_effect=AssertionError("query must not run"))  # type: ignore[method-assign]

    result = await data_manager.get_keyword_statistic_clickhouse(
        client, text="x", adv_ids=set(), pass_days=7
    )
    assert result == (0, 0, 0.0)
