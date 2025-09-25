from __future__ import annotations

from typing import Dict, List

from app.core.mp.wb.promotion_manager import PromotionManager


class MinBidMixin:
    """Mixin for getting minimum bids via PromotionManager."""
    
    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        self.shop_id = shop_id
        self.promotion_manager = promotion_manager

    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Get minimum bids for given nmids in advertisement."""
        return await self.promotion_manager.get_min_bids(
            self.shop_id, adv_id=adv_id, nmids=nmids
        )


class CurrentBidMixin:
    """Mixin for getting current bids via PromotionManager."""
    
    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        self.shop_id = shop_id
        self.promotion_manager = promotion_manager

    async def get_current_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Get current bids for given nmids in advertisement."""
        return await self.promotion_manager.get_current_bids(
            self.shop_id, adv_id=adv_id, nmids=nmids
        )


class BidUpdateMixin:
    """Mixin for updating bids via PromotionManager."""
    
    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        self.shop_id = shop_id
        self.promotion_manager = promotion_manager

    async def update_bids(self, adv_id: int, nm_bids: List[Dict[str, int]]) -> None:
        """Update bids for products in advertisement."""
        await self.promotion_manager.update_bids(
            self.shop_id, adv_id=adv_id, nm_bids=nm_bids
        )
