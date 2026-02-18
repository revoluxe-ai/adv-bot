"""Tests for keyword_bid_from_log module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.keyword_bid_from_log import get_latest_keyword_bids
from app.modules.keyword_bid_from_log.clickhouse_manager import (
    KeywordBidFromLogClickHouseManager,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_latest_keyword_bids_empty_norm_queries_returns_empty_dict() -> None:
    """Call with empty norm_queries does not fail and returns empty dict."""
    result = await get_latest_keyword_bids(adv_id=1, nmids=[100], norm_queries=[])
    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_get_latest_keyword_bids_empty_norm_queries_returns_empty_dict() -> None:
    """Manager returns {} for empty norm_queries without calling CH."""
    manager = KeywordBidFromLogClickHouseManager()
    result = await manager.get_latest_keyword_bids(
        adv_id=1, nmids=[100], norm_queries=[]
    )
    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_get_latest_keyword_bids_returns_map_from_ch_response() -> None:
    """Manager maps CH response to dict norm_query -> (cpm_curr, decision_time)."""
    manager = KeywordBidFromLogClickHouseManager()
    dt = datetime(2025, 2, 17, 12, 0, 0)
    mock_rows = [
        {"norm_query": "query_a", "cpm_curr": 150.5, "decision_time": dt},
        {"norm_query": "query_b", "cpm_curr": 200.0, "decision_time": dt},
    ]
    mock_response = MagicMock()
    mock_response.named_results.return_value = mock_rows

    mock_client = AsyncMock()
    mock_client.query = AsyncMock(return_value=mock_response)

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.keyword_bid_from_log.clickhouse_manager.get_clickhouse_client",
        return_value=mock_context,
    ), patch(
        "app.modules.keyword_bid_from_log.clickhouse_manager.anti_ch_crash_semaphore",
        _DummySemaphore(),
    ):
        result = await manager.get_latest_keyword_bids(
            adv_id=10, nmids=[100, 200], norm_queries=["query_a", "query_b"]
        )

    assert result == {
        "query_a": (150.5, dt),
        "query_b": (200.0, dt),
    }


class _DummySemaphore:
    """Async context manager that does nothing, for bypassing semaphore in tests."""

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, *args: object) -> None:
        pass
