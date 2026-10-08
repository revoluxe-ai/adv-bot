"""ClickHouse history repository tests without network."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.campaign_settings_history.clickhouse_repository import (
    ClickHouseCampaignSettingsHistoryRepository,
)
from app.modules.campaign_settings_history.domain import HistorySnapshotRow

pytestmark = pytest.mark.unit


class FakeClient:
    def __init__(self) -> None:
        self.query_calls: list[tuple[str, dict[str, object]]] = []
        self.insert_calls: list[dict[str, object]] = []
        self.rows: list[tuple[object, ...]] = []

    async def query(self, query: str, parameters=None):
        params = dict(parameters or {})
        self.query_calls.append((query, params))
        rows = list(self.rows)
        start_at = params.get("start_at")
        end_at = params.get("end_at")
        if start_at is not None and "observed_at >=" in query:
            rows = [row for row in rows if row[0] >= start_at]
        if end_at is not None and "observed_at <" in query:
            rows = [row for row in rows if row[0] < end_at]
        return SimpleNamespace(result_rows=rows, column_names=())

    async def insert(
        self,
        table: str,
        data,
        column_names=None,
        database=None,
    ):
        self.insert_calls.append(
            {
                "table": table,
                "data": list(data),
                "column_names": list(column_names or []),
                "database": database,
            }
        )


@pytest.mark.asyncio
async def test_latest_hashes_is_one_qualified_batch_query() -> None:
    client = FakeClient()
    client.rows = [(2, "b" * 64), (1, "a" * 64)]
    repo = ClickHouseCampaignSettingsHistoryRepository(client)

    result = await repo.latest_hashes(77, [1, 2])

    assert result == {2: "b" * 64, 1: "a" * 64}
    assert len(client.query_calls) == 1
    query, params = client.query_calls[0]
    assert "FROM default_db.campaign_settings_history" in query
    assert "argMax(state_hash, tuple(observed_at, snapshot_id))" in query
    assert params == {"wb_cabinet_id": 77, "adv_setting_ids": (1, 2)}


@pytest.mark.asyncio
async def test_empty_latest_hashes_does_not_query() -> None:
    client = FakeClient()
    repo = ClickHouseCampaignSettingsHistoryRepository(client)

    assert await repo.latest_hashes(77, []) == {}
    assert client.query_calls == []


@pytest.mark.asyncio
async def test_insert_uses_default_db_and_exact_history_columns() -> None:
    client = FakeClient()
    repo = ClickHouseCampaignSettingsHistoryRepository(client)
    observed = datetime(2026, 10, 4, tzinfo=UTC)

    await repo.insert_snapshots(
        [
            HistorySnapshotRow(
                observed_at=observed,
                snapshot_id="snap-1",
                adv_setting_id=1,
                wb_cabinet_id=77,
                shop_id="shop-77",
                adv_id=100,
                search_adv_id=None,
                schema_version=1,
                state_hash="a" * 64,
                payload_json='{"schema_version":1}',
            )
        ]
    )

    assert len(client.insert_calls) == 1
    call = client.insert_calls[0]
    assert call["table"] == "campaign_settings_history"
    assert call["database"] == "default_db"
    assert call["column_names"] == [
        "observed_at",
        "snapshot_id",
        "adv_setting_id",
        "wb_cabinet_id",
        "shop_id",
        "adv_id",
        "search_adv_id",
        "schema_version",
        "state_hash",
        "payload_json",
    ]
    assert call["data"][0][0] == observed
    assert call["data"][0][8] == "a" * 64


@pytest.mark.asyncio
async def test_empty_insert_is_noop() -> None:
    client = FakeClient()
    repo = ClickHouseCampaignSettingsHistoryRepository(client)

    await repo.insert_snapshots([])

    assert client.insert_calls == []


@pytest.mark.asyncio
async def test_timeline_is_read_only_and_deterministically_ordered_by_sql() -> None:
    client = FakeClient()
    first = datetime(2026, 10, 1, tzinfo=UTC)
    second = datetime(2026, 10, 2, tzinfo=UTC)
    client.rows = [
        (first, "a", 1, "1" * 64, '{"x":1}'),
        (second, "b", 1, "2" * 64, '{"x":2}'),
    ]
    repo = ClickHouseCampaignSettingsHistoryRepository(client)

    items = await repo.timeline(
        42,
        start_at=first,
        end_at=datetime(2026, 10, 3, tzinfo=UTC),
    )

    assert [item.snapshot_id for item in items] == ["a", "b"]
    query, params = client.query_calls[0]
    assert "FROM default_db.campaign_settings_history" in query
    assert "ORDER BY observed_at, snapshot_id" in query
    assert params["adv_setting_id"] == 42
    assert client.insert_calls == []


@pytest.mark.asyncio
async def test_timeline_up_to_excludes_snapshots_at_or_after_end() -> None:
    client = FakeClient()
    first = datetime(2026, 10, 1, tzinfo=UTC)
    second = datetime(2026, 10, 2, tzinfo=UTC)
    third = datetime(2026, 10, 3, tzinfo=UTC)
    client.rows = [
        (first, "a", 1, "1" * 64, '{"x":1}'),
        (second, "b", 1, "2" * 64, '{"x":2}'),
        (third, "c", 1, "3" * 64, '{"x":3}'),
    ]
    repo = ClickHouseCampaignSettingsHistoryRepository(client)

    items = await repo.timeline_up_to(42, end_at=third)

    assert [item.snapshot_id for item in items] == ["a", "b"]
    query, params = client.query_calls[0]
    assert "observed_at < %(end_at)s" in query
    assert "observed_at >=" not in query
    assert params["end_at"] == third
