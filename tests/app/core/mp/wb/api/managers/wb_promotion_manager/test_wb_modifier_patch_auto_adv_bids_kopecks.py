"""Unit tests for WBModifier.patch_auto_adv_bids_kopecks (values already in kopecks)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import PromotionManager
from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import WBModifier
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)


def _nm_bids_to_map(body: object) -> dict[int, int]:
    assert hasattr(body, "bids") and body.bids
    bids_item = body.bids[0]
    assert hasattr(bids_item, "nm_bids")
    return {item.nm_id: item.bid_kopecks for item in bids_item.nm_bids}



@pytest.fixture
def mock_promotion_manager() -> AsyncMock:
    pm = AsyncMock(spec=PromotionManager)
    pm.patch_adv_v1_bids = AsyncMock()
    return pm


@pytest.fixture
def wb_modifier(mock_promotion_manager: AsyncMock) -> WBModifier:
    return WBModifier(promotion_manager=mock_promotion_manager)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_no_extra_multiply(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    """31000 kopecks must be sent as 31000, not 3100000."""
    await wb_modifier.patch_auto_adv_bids_kopecks(
        adv_id=32824944, nm_bid_kopecks={10749810: 31000}
    )

    mock_promotion_manager.patch_adv_v1_bids.assert_called_once()
    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    kopecks_by_nm = _nm_bids_to_map(body)
    assert kopecks_by_nm[10749810] == 31000


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_uses_recommendations_when_combined_disabled(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    from types import SimpleNamespace

    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(
        return_value=[
            SimpleNamespace(
                settings=SimpleNamespace(
                    placements=SimpleNamespace(
                        recommendations=True,
                        search=False,
                    )
                )
            )
        ]
    )
    await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=32824944, nm_bid_kopecks={1: 31000})
    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    assert (
        body.bids[0].nm_bids[0].placement
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS
    )
