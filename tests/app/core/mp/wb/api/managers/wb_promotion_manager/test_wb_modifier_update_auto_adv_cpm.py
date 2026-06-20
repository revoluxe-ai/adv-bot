"""Unit tests for WBModifier.update_auto_adv_cpm: ensure rubles are converted to kopecks correctly (no 100x bug)."""

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
    bid_type: str = "unified",
    recommendations: bool = True,
    search: bool = True,
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


@pytest.fixture
def mock_promotion_manager() -> AsyncMock:
    pm = AsyncMock(spec=PromotionManager)
    pm.patch_adv_v1_bids = AsyncMock()
    pm.get_adverts_v2_by_ids = AsyncMock(return_value=[_v2_campaign()])
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


def _placement_from_call(call_index: int, mock_pm: AsyncMock) -> object:
    (body,) = mock_pm.patch_adv_v1_bids.call_args_list[call_index][0]
    return body.bids[0].nm_bids[0].placement


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
async def test_update_auto_adv_cpm_placement_combined_for_unified(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    """unified auto-РК: placement combined."""
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(
        return_value=[_v2_campaign(bid_type="unified")]
    )
    await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={1: 10})

    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    for item in body.bids[0].nm_bids:
        assert item.placement == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_placement_recommendations_for_manual_shelf(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(
        return_value=[
            _v2_campaign(
                bid_type="manual",
                recommendations=True,
                search=False,
            )
        ]
    )
    await wb_modifier.update_auto_adv_cpm(adv_id=32824944, nm_bid_pairs={1: 10})

    (body,) = mock_promotion_manager.patch_adv_v1_bids.call_args[0]
    for item in body.bids[0].nm_bids:
        assert (
            item.placement
            == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_unknown_bid_type_retries_combined_first(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(
        return_value=[_v2_campaign(bid_type="")]
    )
    await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={1: 10})
    mock_promotion_manager.patch_adv_v1_bids.assert_called_once()
    assert (
        _placement_from_call(0, mock_promotion_manager)
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_v2_miss_combined_success(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={1: 10})
    mock_promotion_manager.patch_adv_v1_bids.assert_called_once()
    assert (
        _placement_from_call(0, mock_promotion_manager)
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_v2_miss_retries_to_recommendations(
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
    await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={1: 10})
    assert mock_promotion_manager.patch_adv_v1_bids.await_count == 2
    assert (
        _placement_from_call(1, mock_promotion_manager)
        == PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_v2_miss_both_placements_raise(
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
        await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={1: 10})
    assert exc_info.value is last_err


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_auto_adv_cpm_v2_miss_non_placement_error_no_retry(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    mock_promotion_manager.patch_adv_v1_bids = AsyncMock(
        side_effect=BadRequestError(json.dumps({"detail": "invalid bid value"}))
    )
    with pytest.raises(BadRequestError, match="invalid bid value"):
        await wb_modifier.update_auto_adv_cpm(adv_id=1, nm_bid_pairs={1: 10})
    mock_promotion_manager.patch_adv_v1_bids.assert_awaited_once()
