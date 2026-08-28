"""Unit: WBModifier.set_normquery_bids forwards items to promotion set_cluster_bids.

Protects the thin WB_WRITE adapter added for manual common-bid keyword path:
removing the forward would leave callers with a no-op method.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.command import (
    SetNormqueryBidsCommandItem,
)
from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import (
    PromotionManager,
)
from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import (
    WBModifier,
)


@pytest.fixture
def mock_promotion_manager() -> AsyncMock:
    """PromotionManager double with set_cluster_bids awaitable."""
    pm = AsyncMock(spec=PromotionManager)
    pm.set_cluster_bids = AsyncMock()
    return pm


@pytest.fixture
def wb_modifier(mock_promotion_manager: AsyncMock) -> WBModifier:
    """WBModifier wired to the mocked promotion manager."""
    return WBModifier(promotion_manager=mock_promotion_manager)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_set_normquery_bids_forwards_items_to_set_cluster_bids(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    """Adapter must pass the exact bid list to ``set_cluster_bids``."""
    items = [
        SetNormqueryBidsCommandItem(
            advert_id=101,
            nm_id=202,
            norm_query="купить платье",
            bid=150,
        ),
        SetNormqueryBidsCommandItem(
            advert_id=101,
            nm_id=303,
            norm_query="сарафан",
            bid=150,
        ),
    ]

    await wb_modifier.set_normquery_bids(items)

    mock_promotion_manager.set_cluster_bids.assert_awaited_once_with(items)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_set_normquery_bids_empty_list_still_forwards(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    """Empty list still reaches promotion manager (caller owns empty-check)."""
    await wb_modifier.set_normquery_bids([])

    mock_promotion_manager.set_cluster_bids.assert_awaited_once_with([])
