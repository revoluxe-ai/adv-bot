"""PromotionBidsService for managing promotion bid operations."""

from __future__ import annotations

import logging
from typing import Dict, List

from ..promotion_manager import PromotionManager

logger = logging.getLogger(__name__)


class PromotionBidsService:
    """Service for handling promotion bid operations using PromotionManager."""

    def __init__(self, promotion_manager: PromotionManager) -> None:
        """Initialize service with PromotionManager.

        Args:
            promotion_manager: PromotionManager instance for API operations
        """
        self._promotion_manager = promotion_manager
        logger.debug("PromotionBidsService initialized")

    async def resolve_min_bids(self, shop_id: str, adv_id: int, nmids: list[int]) -> dict[int, int]:
        """Resolve minimum bids for given advertisement and product IDs.

        Args:
            shop_id: Shop identifier
            adv_id: Advertisement ID
            nmids: List of product IDs (nmids)

        Returns:
            Dictionary mapping nmid to minimum bid
        """
        logger.debug(f"Resolving min bids for shop_id={shop_id}, adv_id={adv_id}, nmids={nmids}")

        try:
            result = await self._promotion_manager.get_min_bids(shop_id, adv_id=adv_id, nmids=nmids)
            logger.debug(f"Successfully resolved min bids: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to resolve min bids: {e}")
            raise

    async def resolve_current_bids(self, shop_id: str, adv_id: int, nmids: list[int]) -> dict[int, int]:
        """Resolve current bids for given advertisement and product IDs.

        Args:
            shop_id: Shop identifier
            adv_id: Advertisement ID
            nmids: List of product IDs (nmids)

        Returns:
            Dictionary mapping nmid to current bid
        """
        logger.debug(f"Resolving current bids for shop_id={shop_id}, adv_id={adv_id}, nmids={nmids}")

        try:
            result = await self._promotion_manager.get_current_bids(shop_id, adv_id=adv_id, nmids=nmids)
            logger.debug(f"Successfully resolved current bids: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to resolve current bids: {e}")
            raise

    async def update_bids(self, shop_id: str, adv_id: int, nm_bids: list[dict[str, int]]) -> None:
        """Update bids for given advertisement.

        Args:
            shop_id: Shop identifier
            adv_id: Advertisement ID
            nm_bids: List of dicts with 'nm' (nmid) and 'cpm' (bid) keys
        """
        logger.debug(f"Updating bids for shop_id={shop_id}, adv_id={adv_id}, nm_bids={nm_bids}")

        try:
            await self._promotion_manager.update_bids(shop_id, adv_id=adv_id, nm_bids=nm_bids)
            logger.debug("Successfully updated bids")
        except Exception as e:
            logger.error(f"Failed to update bids: {e}")
            raise
