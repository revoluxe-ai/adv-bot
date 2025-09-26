import logging
from typing import Dict, List, cast

from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol

logger = logging.getLogger(__name__)


class GetBidsForNmidsMixin:
    """Mixin that exposes convenience wrapper around promotion adapter bid fetchers."""
    section: str = "promotion"
    version: int = 1
  
    async def get_bids_for_nmid_campaign(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        adapter: PromotionAdapterProtocol = self.get_adapter(self.section, self.version)
        return await adapter.get_current_bids(adv_id=adv_id, nmids=nmids)

