"""Tests for default_db -> disposable ClickHouse rewrite seam."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.support.rewrite_default_db_ch_client import (
    RewritingClickHouseClient,
    TEST_CH_DATABASE,
)

pytestmark = pytest.mark.unit


class _Inner:
    def __init__(self) -> None:
        self.insert_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.query_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def insert(self, *args, **kwargs):
        self.insert_calls.append((args, dict(kwargs)))

    async def query(self, *args, **kwargs):
        self.query_calls.append((args, dict(kwargs)))
        return SimpleNamespace(result_rows=[])

    def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_insert_rewrites_default_db_database_kwarg() -> None:
    """Test seam preserves production call shape before mapping to disposable DB."""
    inner = _Inner()
    client = RewritingClickHouseClient(inner)

    await client.insert(
        "campaign_settings_history",
        [[1]],
        column_names=["x"],
        database="default_db",
    )

    args, kwargs = inner.insert_calls[0]
    assert args[0] == "campaign_settings_history"
    assert kwargs["database"] == TEST_CH_DATABASE


@pytest.mark.asyncio
async def test_query_rewrites_default_db_qualifier() -> None:
    """Production-qualified SQL is redirected only inside the test seam."""
    inner = _Inner()
    client = RewritingClickHouseClient(inner)

    await client.query("SELECT * FROM default_db.campaign_settings_history")

    args, _ = inner.query_calls[0]
    assert args[0] == (
        "SELECT * FROM "
        f"{TEST_CH_DATABASE}.campaign_settings_history"
    )
