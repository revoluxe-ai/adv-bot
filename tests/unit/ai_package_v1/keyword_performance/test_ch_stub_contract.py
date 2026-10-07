"""S37/S38 stub contract parity: production readers vs boundary fakes."""

from __future__ import annotations

from datetime import date
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    ChBidDecisionProbe,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader import (
    ChBidDecisionReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
    ChKeywordBoundsReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader import (
    ChKeywordDailyReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    ChKeywordPositionReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_adv_id_overlap_reader import (
    PgAdvIdOverlapReader,
)
from tests.unit.ai_package_v1.keyword_performance.boundary_fakes import (
    FakeClickHouseClient,
    FakePgSession,
    fake_pg_session_maker,
)

pytestmark = pytest.mark.unit

CUTOFF = PackageCutoff.from_generated_at("2026-01-07T12:00:00Z")


def _params(call: Any) -> dict[str, Any]:
    raw = call.kwargs.get("parameters")
    if raw is None and len(call.args) > 1:
        raw = call.args[1]
    return cast(dict[str, Any], raw)


@pytest.mark.asyncio
async def test_stub_contract_daily_reader_routing_and_cutoff_params() -> None:
    """FakeClickHouseClient + ChKeywordDailyReader share cutoff parameter contract."""
    client = FakeClickHouseClient()
    reader = ChKeywordDailyReader()
    _ = await reader.fetch_rows_with_client(
        client,
        adv_ids=frozenset({111, 222}),
        first_available=date(2026, 1, 1),
        cutoff=CUTOFF,
    )
    assert client.query.await_count >= 1
    params = _params(client.query.await_args_list[0])
    assert isinstance(params["adv_ids"], list)
    adv_ids = cast(list[int], params["adv_ids"])
    assert set(adv_ids) == {111, 222}
    assert params["first_available"] == "2026-01-01"
    assert params["package_cutoff_date"] == "2026-01-07"
    assert params["package_cutoff_instant"] == "2026-01-07 12:00:00"
    sql = client.query.await_args_list[0].args[0]
    assert "timestamp <= {package_cutoff_instant:DateTime}" in reader.query_text
    assert "clusters_adv_stats" in sql or "keyword_daily_from_clusters" in sql


@pytest.mark.asyncio
async def test_stub_contract_position_reader_routing_and_version_ms() -> None:
    """Position reader passes cutoff_instant_ms through FakeClickHouseClient seam."""
    client = FakeClickHouseClient()
    reader = ChKeywordPositionReader()
    _ = await reader.fetch_rows_with_client(
        client,
        nmids=frozenset({500}),
        position_first_available=date(2026, 1, 1),
        cutoff=CUTOFF,
    )
    params = _params(client.query.await_args)
    assert params["nmids"] == [500]
    assert params["position_first_available"] == "2026-01-01"
    assert params["package_cutoff_date"] == "2026-01-07"
    assert params["cutoff_instant_ms"] == CUTOFF.cutoff_instant_ms
    assert "version <= {cutoff_instant_ms" in reader.query_text


@pytest.mark.asyncio
async def test_stub_contract_bounds_reader_daily_and_position_queries() -> None:
    """Bounds reader issues independent daily/position SQL with cutoff predicates."""
    client = FakeClickHouseClient()
    bounds = ChKeywordBoundsReader()
    daily = await bounds.fetch_daily_bounds_with_client(
        client, frozenset({111}), CUTOFF
    )
    position = await bounds.fetch_position_bounds_with_client(
        client, frozenset({500}), CUTOFF
    )
    assert daily.first_available == date(2026, 1, 1)
    assert daily.last_available == date(2026, 1, 5)
    assert position.first_available == date(2026, 1, 1)
    assert position.last_available == date(2026, 1, 5)
    sqls = [call.args[0] for call in client.query.await_args_list]
    assert any("keyword_history_bounds" in sql or "clusters_adv_stats" in sql for sql in sqls)
    assert any("keyword_position_bounds" in sql for sql in sqls)
    daily_params = _params(client.query.await_args_list[0])
    assert daily_params["package_cutoff_date"] == "2026-01-07"
    pos_params = _params(client.query.await_args_list[1])
    assert pos_params["cutoff_instant_ms"] == CUTOFF.cutoff_instant_ms


@pytest.mark.asyncio
async def test_stub_contract_bid_probe_schema_and_sample_cutoff() -> None:
    """Bid probe uses FakeClickHouseClient routing for schema + sample queries."""
    client = FakeClickHouseClient()
    probe = ChBidDecisionProbe()
    result = await probe.probe_with_client(client, adv_ids=frozenset({111}), cutoff=CUTOFF)
    assert result.status.value in {"AVAILABLE", "AVAILABLE_EMPTY", "UNSUPPORTED", "FAILED"}
    assert client.query.await_count >= 2
    sample_call = client.query.await_args_list[-1]
    sample_params = _params(sample_call)
    assert sample_params["package_cutoff_instant"] == "2026-01-07 12:00:00"
    sample_sql = sample_call.args[0]
    assert "decision_time <= {package_cutoff_instant:DateTime}" in sample_sql


@pytest.mark.asyncio
async def test_stub_contract_bid_decision_reader_timeline_params() -> None:
    """Timeline reader passes package_cutoff_instant via fake client."""
    client = FakeClickHouseClient()
    reader = ChBidDecisionReader()
    _ = await reader.fetch_timeline_with_client(
        client, adv_ids=frozenset({111}), cutoff=CUTOFF
    )
    params = _params(client.query.await_args)
    assert params["adv_ids"] == [111]
    assert params["package_cutoff_instant"] == "2026-01-07 12:00:00"
    assert "decision_time <= {package_cutoff_instant:DateTime}" in reader.timeline_query_text
    assert "tuple_variants_at_max_version" in reader.latest_query_text


@pytest.mark.asyncio
async def test_stub_contract_unknown_sql_fail_closed_empty_rows() -> None:
    """Unknown CH SQL through FakeClickHouseClient returns empty rows (fail-closed)."""
    client = FakeClickHouseClient()
    result = await client.query("SELECT 1 FROM unknown_table")
    assert result.result_rows == []


@pytest.mark.asyncio
async def test_stub_contract_fake_session_forbids_commit() -> None:
    """_FakeSession mirrors read-only PG seam: commit forbidden."""
    session = FakePgSession()
    async with session:
        result = await session.execute(MagicMock())
        assert result.scalars().all() == []
    with pytest.raises(AssertionError, match="PG commit forbidden"):
        await session.commit()


@pytest.mark.asyncio
async def test_stub_contract_pg_overlap_reader_read_only_session() -> None:
    """PgAdvIdOverlapReader with _fake_session_maker completes without commit."""
    reader = PgAdvIdOverlapReader(fake_pg_session_maker)
    overlap = await reader.load_overlap(frozenset({111, 222}))
    assert overlap == {}


@pytest.mark.asyncio
async def test_pg_overlap_reader_null_adv_id_row_is_excluded() -> None:
    """NULL adv_id is omitted, not zero-filled; sibling identities stay."""
    rows: list[tuple[object, object, object, object]] = [
        ("shop-null", 10, None, None),
        ("shop-real", 11, 111, None),
        ("shop-search", 12, None, 222),
    ]
    result = MagicMock()
    result.all = MagicMock(return_value=rows)
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    reader = PgAdvIdOverlapReader(fake_pg_session_maker)
    overlap = await reader.load_overlap(
        frozenset({111, 222, 0}),
        session=cast(Any, session),
    )
    assert 0 not in overlap
    assert overlap == {
        111: [("shop-real", 11)],
        222: [("shop-search", 12)],
    }


@pytest.mark.asyncio
async def test_stub_contract_daily_reader_coherent_nullable_tuple_shape() -> None:
    """Daily reader parses coherent vs ambiguous tuple rows from fake client."""
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=MagicMock(
            result_rows=[
                (
                    111,
                    500,
                    "q",
                    date(2026, 1, 3),
                    None,
                    2,
                    (3.0, 100, 1, 1_700_000_000_000),
                ),
                (
                    111,
                    500,
                    "q2",
                    date(2026, 1, 4),
                    None,
                    1,
                    (100, 10, 5, 2, 50.0, 100.0, 5.0, 5.0, 0.1),
                ),
            ]
        )
    )
    reader = ChKeywordDailyReader()
    rows = await reader.fetch_rows_with_client(
        client,
        adv_ids=frozenset({111}),
        first_available=date(2026, 1, 1),
        cutoff=CUTOFF,
    )
    assert len(rows) == 2
    assert rows[0].snapshot_variants_at_max_ts == 2
    assert rows[0].views is None
    assert rows[1].views == 100


@pytest.mark.asyncio
async def test_stub_contract_position_reader_future_version_parse_then_guard() -> None:
    """Position reader parses future-version row; assembler guard excludes it downstream."""
    from datetime import UTC, datetime

    from app.modules.ai_package_v1.keyword_performance.domain.cutoff_guard import (
        filter_position_rows,
    )

    future_version = int(datetime(2026, 1, 7, 15, 0, 0, tzinfo=UTC).timestamp() * 1000)
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=MagicMock(
            result_rows=[
                (
                    500,
                    "query",
                    date(2026, 1, 7),
                    future_version,
                    1,
                    (3.5, 100, 1, future_version),
                )
            ]
        )
    )
    reader = ChKeywordPositionReader()
    rows = await reader.fetch_rows_with_client(
        client,
        nmids=frozenset({500}),
        position_first_available=date(2026, 1, 1),
        cutoff=CUTOFF,
    )
    assert len(rows) == 1
    filtered = filter_position_rows(rows, CUTOFF)
    assert filtered == []
