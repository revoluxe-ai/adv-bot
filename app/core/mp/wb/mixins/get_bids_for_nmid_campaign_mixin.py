import logging
from typing import Dict, List, cast

from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol

logger = logging.getLogger(__name__)


class GetBidsForNmidCampaignMixin:
    """Mixin that exposes convenience wrapper around promotion adapter bid fetchers."""

    promotion_adapter_version: str = "v1"

    def _promotion_adapter(self) -> PromotionAdapterProtocol:
        return cast(PromotionAdapterProtocol, self.get_adapter("promotion", self.promotion_adapter_version))

    async def get_bids_for_nmid_campaign(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        if not adv_id:
            raise ValueError("adv_id must be positive")
        if not nmids:
            return {}
        adapter = self._promotion_adapter()
        return await adapter.get_current_bids(adv_id=adv_id, nmids=nmids)
