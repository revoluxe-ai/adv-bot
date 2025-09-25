from __future__ import annotations

from typing import Dict, Tuple, List
import time

from app.core.mp.wb.managers.promotion import PromotionManager


class PromotionBidsService:
    """Service layer that uses PromotionManager and provides a small in-memory cache

    Caches min_bids results for `ttl_seconds` to avoid repeated WB API calls.
    """

    def __init__(self, promotion_manager: PromotionManager, ttl_seconds: int = 30) -> None:
        self.promotion_manager = promotion_manager
        self._ttl = ttl_seconds
        # key: (shop_id, adv_id, tuple(nmids)) -> (timestamp, result_dict)
        self._cache: Dict[Tuple[str, int, Tuple[int, ...]], Tuple[float, Dict[int, int]]] = {}

    async def resolve_min_bids(self, shop_id: str, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        key = (shop_id, adv_id, tuple(nmids))
        now = time.time()
        entry = self._cache.get(key)
        if entry is not None:
            ts, value = entry
            if now - ts < self._ttl:
                return value

        result = await self.promotion_manager.get_min_bids(shop_id, adv_id, nmids)
        # store timestamped copy
        self._cache[key] = (now, result)
        return result

    async def resolve_current_bids(self, shop_id: str, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        return await self.promotion_manager.get_current_bids(shop_id, adv_id, nmids)

    async def update_bids(self, shop_id: str, batch: object) -> None:
        await self.promotion_manager.update_bids(shop_id, batch)


