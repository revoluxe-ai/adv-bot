"""Unit tests for min bids Redis cache v2 (adv + placement + nmid)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_min_bids_cache_manager import (
    MIN_BIDS_V2_DEFAULT_TTL_SEC,
    MinBidsCacheManager,
)


@pytest.mark.asyncio
async def test_set_min_bid_v2_uses_key_ttl_and_json() -> None:
    mock_client = AsyncMock()
    mgr = MinBidsCacheManager(mock_client)

    await mgr.set_min_bid_for_adv_placement_nmid(
        42,
        AdvPlacementType.AUTO_ADV,
        999001,
        150,
    )

    mock_client.set.assert_called_once()
    key, payload = mock_client.set.call_args[0][:2]
    assert key == (
        "min_bids:v2:adv:42:pt:auto_adv:nmid:999001"
    )
    assert json.loads(payload) == {"cpm": 150}
    kwargs = mock_client.set.call_args.kwargs
    assert kwargs.get("ex") == MIN_BIDS_V2_DEFAULT_TTL_SEC


@pytest.mark.asyncio
async def test_get_min_bid_v2_parses_cpm() -> None:
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        return_value=json.dumps({"cpm": 77}),
    )
    mgr = MinBidsCacheManager(mock_client)

    out = await mgr.get_min_bid_for_adv_placement_nmid(
        1,
        AdvPlacementType.SEARCH_ADV,
        12,
    )

    assert out == 77
    mock_client.get.assert_called_once_with(
        "min_bids:v2:adv:1:pt:search_adv:nmid:12"
    )


@pytest.mark.asyncio
async def test_get_min_bid_v2_miss_returns_none() -> None:
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mgr = MinBidsCacheManager(mock_client)

    assert (
        await mgr.get_min_bid_for_adv_placement_nmid(
            1,
            AdvPlacementType.AUTO_ADV,
            1,
        )
        is None
    )


@pytest.mark.asyncio
async def test_get_min_bids_v2_batch_uses_mget() -> None:
    mock_client = AsyncMock()
    mock_client.mget = AsyncMock(
        return_value=[
            json.dumps({"cpm": 10}),
            None,
        ]
    )
    mgr = MinBidsCacheManager(mock_client)
    cells = [
        (1, AdvPlacementType.AUTO_ADV, 100),
        (1, AdvPlacementType.AUTO_ADV, 101),
    ]
    out = await mgr.get_min_bids_v2_batch(cells)
    assert out[(1, AdvPlacementType.AUTO_ADV, 100)] == 10
    assert len(out) == 1
    mock_client.mget.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_min_bids_v2_batch_uses_pipeline() -> None:
    pipeline = MagicMock()
    pipeline.set = MagicMock()
    pipeline.execute = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=pipeline)
    cm.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.write_pipeline = MagicMock(return_value=cm)

    mgr = MinBidsCacheManager(mock_client)
    await mgr.set_min_bids_v2_batch(
        [(42, AdvPlacementType.SEARCH_ADV, 7, 55)],
    )

    pipeline.set.assert_called_once()
    pipeline.execute.assert_awaited_once()
