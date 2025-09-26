from __future__ import annotations

from typing import Dict, List


class CurrentBidMixin:

    async def get_current_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Delegate to PromotionManager.get_current_bids with stored shop_id."""
        return await self.promotion_manager.get_current_bids(self.shop_id, adv_id, nmids)
