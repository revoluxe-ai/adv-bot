"""PromotionV2RawReadAdapter delegation tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter import (
    CampaignsInfoV2Adapter,
)
from app.modules.wb_sky_control_plane.read.wb_reader import PromotionV2RawReadAdapter

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_wb_reader_delegates_to_adapter_raw_method() -> None:
    """A1 reader must delegate to CampaignsInfoV2Adapter.get_campaigns_info_raw_by_ids."""
    adapter = MagicMock(spec=CampaignsInfoV2Adapter)
    adapter.get_campaigns_info_raw_by_ids = AsyncMock(
        return_value=[{"id": 101, "bid_type": "unified"}]
    )
    reader = PromotionV2RawReadAdapter(adapter)
    items = await reader.fetch_adverts_raw_by_ids([101])
    adapter.get_campaigns_info_raw_by_ids.assert_awaited_once_with([101])
    assert items[0]["id"] == 101
