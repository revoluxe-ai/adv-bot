"""WB promotion v2 read adapter extension (raw JSON, reuse existing transport)."""

from __future__ import annotations

from collections.abc import Mapping

from app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter import (
    CampaignsInfoV2Adapter,
)
from app.modules.wb_sky_control_plane.ports.wb_read_port import WbPromotionV2ReadPort


class PromotionV2RawReadAdapter(WbPromotionV2ReadPort):
    """Reuse CampaignsInfoV2Adapter HTTP path; parse raw JSON for strict normalizer."""

    def __init__(self, campaigns_info_v2_adapter: CampaignsInfoV2Adapter) -> None:
        self._adapter = campaigns_info_v2_adapter

    async def fetch_adverts_raw_by_ids(
        self, adv_ids: list[int]
    ) -> list[Mapping[str, object]]:
        """Delegate to CampaignsInfoV2Adapter raw method (retry/rate-limit preserved)."""
        return await self._adapter.get_campaigns_info_raw_by_ids(adv_ids)
