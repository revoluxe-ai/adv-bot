from __future__ import annotations

import logging
import time
from typing import Dict, List, Tuple

from ..managers.promotion import PromotionManager

logger = logging.getLogger(__name__)


class PromotionBidsService:
    """Service for handling promotion bid operations using PromotionManager.
    
    Caches `min_bids` for `ttl_seconds` to avoid redundant WB API calls.
    """

    def __init__(self, promotion_manager: PromotionManager, ttl_seconds: int = 30) -> None:
        self._promotion_manager = promotion_manager
        self._ttl = ttl_seconds
        # key: (shop_id, adv_id, tuple(nmids)) -> (timestamp, result_dict)
        self._cache: Dict[Tuple[str, int, Tuple[int, ...]], Tuple[float, Dict[int, int]]] = {}
        logger.debug("PromotionBidsService initialized")

    async def resolve_min_bids(self, shop_id: str, adv_id: int, nmids: list[int]) -> dict[int, int]:
        logger.debug(f"Resolving min bids for shop_id={shop_id}, adv_id={adv_id}, nmids={nmids}")

        key = (shop_id, adv_id, tuple(nmids))
        now = time.time()
        entry = self._cache.get(key)

        if entry:
            ts, value = entry
            if now - ts < self._ttl:
                logger.debug(f"Cache hit for {key}")
                return value

        try:
            result = await self._promotion_manager.get_min_bids(shop_id, adv_id=adv_id, nmids=nmids)
            self._cache[key] = (now, result)
            logger.debug(f"Successfully resolved min bids: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to resolve min bids: {e}")
            raise

    async def resolve_current_bids(self, shop_id: str, adv_id: int, nmids: list[int]) -> dict[int, int]:
        logger.debug(f"Resolving current bids for shop_id={shop_id}, adv_id={adv_id}, nmids={nmids}")
        try:
            return await self._promotion_manager.get_current_bids(shop_id, adv_id=adv_id, nmids=nmids)
        except Exception as e:
            logger.error(f"Failed to resolve current bids: {e}")
            raise

    async def update_bids(self, shop_id: str, adv_id: int, nm_bids: list[dict[str, int]]) -> None:
        logger.debug(f"Updating bids for shop_id={shop_id}, adv_id={adv_id}, nm_bids={nm_bids}")
        try:
            await self._promotion_manager.update_bids(shop_id, adv_id=adv_id, nm_bids=nm_bids)
            logger.debug("Successfully updated bids")
        except Exception as e:
            logger.error(f"Failed to update bids: {e}")
            raise
