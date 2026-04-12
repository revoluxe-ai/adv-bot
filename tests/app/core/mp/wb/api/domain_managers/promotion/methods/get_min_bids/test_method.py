"""Tests for get_min_bids domain method (aggregation after adapter partial results)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.min_bids.adapter import MinBidsAdapter
from app.core.mp.wb.api.adapter.promotion_client.min_bids.dto import MinBidForNmid
from app.core.mp.wb.api.domain_managers.promotion.methods.get_min_bids.method import (
    get_min_bids,
)
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType


@pytest.mark.asyncio
async def test_get_min_bids_empty_advs_returns_none() -> None:
    adapter = AsyncMock(spec=MinBidsAdapter)
    assert await get_min_bids(adapter, []) is None
    adapter.post_api_advert_v1_bids_min.assert_not_called()


@pytest.mark.asyncio
async def test_get_min_bids_partial_nmids_still_builds_adv_min_nmids_bids() -> None:
    """Adapter may return fewer MinBidForNmid than requested nmids; aggregation stays valid."""
    adapter = AsyncMock(spec=MinBidsAdapter)
    adapter.post_api_advert_v1_bids_min = AsyncMock(
        return_value=[
            MinBidForNmid(
                nmid=1,
                placement_type=AdvPlacementType.AUTO_ADV,
                min_cpm=250,
            ),
        ]
    )
    adv = MagicMock()
    adv.nmids = [1, 2]
    adv.auto_adv_id = 100
    adv.search_adv_id = None

    result = await get_min_bids(adapter, [adv])

    assert result is not None
    assert result.auto == {1: (250 + 99) // 100}
    assert result.search == {}
