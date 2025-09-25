from __future__ import annotations

from typing import Dict, List

from app.core.mp.wb.managers.promotion import PromotionManager


class MinBidMixin:
    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        self.shop_id = shop_id
        self.promotion_manager = promotion_manager

    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Proxy to PromotionManager.get_min_bids"""
        return await self.promotion_manager.get_min_bids(self.shop_id, adv_id, nmids)


class CurrentBidMixin:
    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        self.shop_id = shop_id
        self.promotion_manager = promotion_manager

    async def get_current_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Proxy to PromotionManager.get_current_bids"""
        return await self.promotion_manager.get_current_bids(self.shop_id, adv_id, nmids)


class BidUpdateMixin:
    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        self.shop_id = shop_id
        self.promotion_manager = promotion_manager

    async def update_bids(self, batch: object) -> None:
        """Proxy to PromotionManager.update_bids"""
        return await self.promotion_manager.update_bids(self.shop_id, batch)
