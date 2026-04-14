"""Chunking for POST /adv/v0/normquery/get-bids (max 100 items per request)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.api.domain_managers.promotion.methods.get_current_bids.method import (
    MAX_ITEMS_PER_REQUEST,
    get_current_bids,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryBidsRequest,
    V0GetNormQueryBidsRequestItem,
)


def _bid(advert_id: int, nm_id: int) -> NormqueryBidDTO:
    return NormqueryBidDTO(
        advert_id=advert_id,
        nm_id=nm_id,
        norm_query="q",
        bid=1,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_current_bids_splits_requests_when_over_100_items() -> None:
    items = [
        V0GetNormQueryBidsRequestItem(advert_id=1, nm_id=i) for i in range(150)
    ]
    full_command = V0GetNormQueryBidsRequest(items=items)

    adapter = MagicMock()
    adapter.post_adv_v0_normquery_get_bids = AsyncMock(
        side_effect=[
            [_bid(1, i) for i in range(100)],
            [_bid(1, i) for i in range(100, 150)],
        ]
    )

    dummy_adv = MagicMock()
    with patch(
        "app.core.mp.wb.api.domain_managers.promotion.methods.get_current_bids.method.convertor.dto_to_request",
        return_value=full_command,
    ):
        result = await get_current_bids(adapter, [dummy_adv])

    assert adapter.post_adv_v0_normquery_get_bids.call_count == 2
    first_call = adapter.post_adv_v0_normquery_get_bids.call_args_list[0][0][0]
    second_call = adapter.post_adv_v0_normquery_get_bids.call_args_list[1][0][0]
    assert len(first_call.items) == MAX_ITEMS_PER_REQUEST
    assert len(second_call.items) == 50
    assert result is not None
    assert len(result) == 150


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_current_bids_keeps_partial_data_when_chunk_returns_none() -> None:
    items = [
        V0GetNormQueryBidsRequestItem(advert_id=1, nm_id=i) for i in range(150)
    ]
    full_command = V0GetNormQueryBidsRequest(items=items)

    adapter = MagicMock()
    adapter.post_adv_v0_normquery_get_bids = AsyncMock(
        side_effect=[None, [_bid(1, i) for i in range(100, 150)]]
    )

    with patch(
        "app.core.mp.wb.api.domain_managers.promotion.methods.get_current_bids.method.convertor.dto_to_request",
        return_value=full_command,
    ):
        result = await get_current_bids(adapter, [MagicMock()])

    assert result is not None
    assert len(result) == 50
    assert adapter.post_adv_v0_normquery_get_bids.call_count == 2
