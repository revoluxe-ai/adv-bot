"""Unit tests for WBModifier.update_auto_adv_cpm: ensure rubles are converted to kopecks correctly (no 100x bug)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import PromotionManager
from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import WBModifier
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)


@pytest.fixture
def mock_promotion_manager() -> AsyncMock:
    pm = AsyncMock(spec=PromotionManager)
    pm.patch_adv_v1_bids = AsyncMock()
    return pm


@pytest.fixture
def wb_modifier(mock_promotion_manager: AsyncMock) -> WBModifier:
    return WBModifier(promotion_manager=mock_promotion_manager)


def _nm_bids_to_map(body: object) -> dict[int, int]:
    """Extract nm_id -> bid_kopecks from the body passed to patch_adv_v1_bids."""
    assert hasattr(body, "bids") and body.bids
    bids_item = body.bids[0]
    assert hasattr(bids_item, "nm_bids")
    return {item.nm_id: item.bid_kopecks for item in bids_item.nm_bids}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_sends_rubles_as_kopecks(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    """Input in rubles must be sent as kopecks (rub * 100). Prevents sending rubles as kopecks (100x overbid)."""
    adv_id = 999
    nm_bid_pairs = {111: 50, 222: 100}  # 50 rub, 100 rub

    await wb_modifier.update_auto_adv_cpm(adv_id=adv_id, nm_bid_pairs=nm_bid_pairs)

    mock_promotion_manager.patch_adv_v1_bids.assert_called_once()
    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    assert body.bids[0].advert_id == adv_id
    kopecks_by_nm = _nm_bids_to_map(body)

    assert kopecks_by_nm[111] == 5000, "50 rub must be 5000 kopecks, not 50 (would be 100x overbid)"
    assert kopecks_by_nm[222] == 10000, "100 rub must be 10000 kopecks, not 100 (would be 100x overbid)"
    for nm_id, bid_rub in nm_bid_pairs.items():
        assert kopecks_by_nm[nm_id] == bid_rub * 100


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_one_rub_is_100_kopecks(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    """1 rub must become 100 kopecks. Catches: (1) sending rubles as kopecks -> 1 kopeck; (2) double *100 -> 10000."""
    await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={12345: 1})

    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    kopecks_by_nm = _nm_bids_to_map(body)
    assert kopecks_by_nm[12345] == 100, "1 rub must be 100 kopecks (not 1 and not 10000)"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_placement_combined(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    """Auto campaign must use COMBINED placement for v1 bids."""
    await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={1: 10})

    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    for item in body.bids[0].nm_bids:
        assert item.placement == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
