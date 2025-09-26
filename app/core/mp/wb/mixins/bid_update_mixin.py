from __future__ import annotations

from app.core.mp.wb.managers.promotion import PromotionManager


class BidUpdateMixin:
    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        self.shop_id = shop_id
        self.promotion_manager = promotion_manager

    async def update_bids(self, batch: object) -> None:
        """Delegate to PromotionManager.update_bids with stored shop_id."""
        return await self.promotion_manager.update_bids(self.shop_id, batch)
