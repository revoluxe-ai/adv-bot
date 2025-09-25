from __future__ import annotations

from typing import Dict, List


class PromotionManager:
    """Business manager interface composed from mixins for promotion operations."""

    async def get_min_bids(self, shop_id: str, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        raise NotImplementedError

    async def get_current_bids(self, shop_id: str, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        raise NotImplementedError

    async def update_bids(self, batch: object) -> None:
        raise NotImplementedError
