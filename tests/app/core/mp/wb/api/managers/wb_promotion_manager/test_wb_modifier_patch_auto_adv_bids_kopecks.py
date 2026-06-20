"""Unit tests for WBModifier.patch_auto_adv_bids_kopecks (values already in kopecks)."""

from __future__ import annotations

import json

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import PromotionManager
from app.core.mp.wb.api.excs import BadRequestError
from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import WBModifier
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)


def _v2_campaign(
    *,
    bid_type: str = "manual",
    recommendations: bool = True,
    search: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        bid_type=bid_type,
        settings=SimpleNamespace(
            placements=SimpleNamespace(
                recommendations=recommendations,
                search=search,
            )
        ),
    )


def _placement_error(detail: str) -> BadRequestError:
    return BadRequestError(json.dumps({"detail": detail}))


def _nm_bids_to_map(body: object) -> dict[int, int]:
    assert hasattr(body, "bids") and body.bids
    bids_item = body.bids[0]
    assert hasattr(bids_item, "nm_bids")
    return {item.nm_id: item.bid_kopecks for item in bids_item.nm_bids}


def _placement_from_call(call_index: int, mock_pm: AsyncMock) -> object:
    (body,) = mock_pm.patch_adv_v1_bids.call_args_list[call_index][0]
    return body.bids[0].nm_bids[0].placement


@pytest.fixture
def mock_promotion_manager() -> AsyncMock:
    pm = AsyncMock(spec=PromotionManager)
    pm.patch_adv_v1_bids = AsyncMock()
    pm.get_adverts_v2_by_ids = AsyncMock(return_value=[])
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
    assert (
        body.bids[0].nm_bids[0].placement
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_uses_recommendations_for_manual_shelf(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(
        return_value=[_v2_campaign(bid_type="manual", recommendations=True, search=False)]
    )
    await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=32824944, nm_bid_kopecks={1: 31000})
    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    assert (
        body.bids[0].nm_bids[0].placement
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_unified_uses_combined(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(
        return_value=[_v2_campaign(bid_type="unified", recommendations=True, search=True)]
    )
    await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=35757631, nm_bid_kopecks={1: 31000})
    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    assert (
        body.bids[0].nm_bids[0].placement
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_unknown_bid_type_retries_combined_first(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(
        return_value=[_v2_campaign(bid_type="legacy")]
    )
    await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=1, nm_bid_kopecks={1: 100})
    mock_promotion_manager.patch_adv_v1_bids.assert_called_once()
    assert (
        _placement_from_call(0, mock_promotion_manager)
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_v2_miss_combined_success(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=1, nm_bid_kopecks={1: 100})
    mock_promotion_manager.patch_adv_v1_bids.assert_called_once()
    assert (
        _placement_from_call(0, mock_promotion_manager)
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_v2_miss_retries_to_recommendations(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    mock_promotion_manager.patch_adv_v1_bids = AsyncMock(
        side_effect=[
            _placement_error("combined placement is disabled"),
            None,
        ]
    )
    await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=1, nm_bid_kopecks={1: 100})
    assert mock_promotion_manager.patch_adv_v1_bids.await_count == 2
    assert (
        _placement_from_call(0, mock_promotion_manager)
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
    )
    assert (
        _placement_from_call(1, mock_promotion_manager)
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_v2_miss_both_placements_raise(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    last_err = _placement_error("invalid target type recom")
    mock_promotion_manager.patch_adv_v1_bids = AsyncMock(
        side_effect=[
            _placement_error("combined placement is disabled"),
            last_err,
        ]
    )
    with pytest.raises(BadRequestError) as exc_info:
        await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=1, nm_bid_kopecks={1: 100})
    assert exc_info.value is last_err
    assert mock_promotion_manager.patch_adv_v1_bids.await_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_patch_auto_adv_bids_kopecks_v2_miss_non_placement_error_no_retry(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    mock_promotion_manager.patch_adv_v1_bids = AsyncMock(
        side_effect=BadRequestError(json.dumps({"detail": "invalid bid value"}))
    )
    with pytest.raises(BadRequestError, match="invalid bid value"):
        await wb_modifier.patch_auto_adv_bids_kopecks(adv_id=1, nm_bid_kopecks={1: 100})
    mock_promotion_manager.patch_adv_v1_bids.assert_awaited_once()
