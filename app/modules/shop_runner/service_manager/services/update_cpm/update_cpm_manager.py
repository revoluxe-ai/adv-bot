import asyncio
import logging
from typing import Awaitable, Dict, List, Optional

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition
from app.core.mp.wb.promotion_manager import PromotionManager
from app.core.mp.wb.mixins.bid_update import MinBidMixin, CurrentBidMixin, BidUpdateMixin
from app.modules.wb_adv_updater import data_manager
from app.utils import redis_manager
from .bid_calculator import BidCalculator, BidCalculationParams

logger = logging.getLogger(__name__)


class UpdateCPMManager(MinBidMixin, CurrentBidMixin, BidUpdateMixin):
    """CPM update manager using mixins and PromotionManager via DI."""
    
    _DEFAULT_BIDDER_STEP = 2

    def __init__(self, shop_id: str, promotion_manager: PromotionManager) -> None:
        """Initialize with shop_id and PromotionManager via DI.
        
        Args:
            shop_id: Shop identifier
            promotion_manager: PromotionManager instance from DI container
        """
        self._shop_id = shop_id
        self._promotion_manager = promotion_manager
        
        # Initialize mixins
        MinBidMixin.__init__(self, shop_id, promotion_manager)
        CurrentBidMixin.__init__(self, shop_id, promotion_manager)
        BidUpdateMixin.__init__(self, shop_id, promotion_manager)
        
        self._bid_calculator = BidCalculator()

    async def update_cpms_in_search_advs(
        self, adv_settings_and_keywords_coro: List[tuple[AdvSetting, Awaitable[List[CalculatedKeyword]]]]
    ) -> None:
        """Update CPM bids for search advertisements.
        
        Args:
            adv_settings_and_keywords_coro: List of tuples containing AdvSetting and coroutine for keywords
        """
        if not adv_settings_and_keywords_coro:
            logger.debug("No advertisements to process")
            return

        # Process each advertisement campaign
        for adv, keywords_coro in adv_settings_and_keywords_coro:
            try:
                await self._process_single_adv(adv, keywords_coro)
            except Exception as e:
                logger.error(f"Failed to process adv {adv.search_adv_id}: {e}")
                continue

    async def _process_single_adv(
        self, adv: AdvSetting, keywords_coro: Awaitable[List[CalculatedKeyword]]
    ) -> None:
        """Process a single advertisement campaign.
        
        Args:
            adv: Advertisement settings
            keywords_coro: Coroutine that returns calculated keywords
        """
        search_adv_id = adv.search_adv_id
        nmids = adv.nmids
        max_bid = adv.max_cpm
        target_position = adv.max_place
        bidder_step = adv.bidder_step or self._DEFAULT_BIDDER_STEP

        if not search_adv_id or not nmids or not max_bid or not target_position:
            logger.debug(f"Skip: missing required params for adv {search_adv_id}")
            return
            
        # Type check for search_adv_id
        if not isinstance(search_adv_id, int):
            logger.debug(f"Skip: invalid search_adv_id type for adv {search_adv_id}")
            return

        try:
            # Get keywords and pick the best one
            keywords = await keywords_coro
            best_keyword = data_manager.get_best_keyword(keywords) if keywords else None
            
            if not best_keyword:
                logger.debug(f"Skip: no best keyword for adv {search_adv_id}")
                return

            # Get bids data via mixins
            min_bids_map = await self.get_min_bids(search_adv_id, nmids)
            current_bids_map = await self.get_current_bids(search_adv_id, nmids)

            # Process each nmid
            bid_updates = []
            for nmid in nmids:
                new_bid = await self._calculate_new_bid_for_nmid(
                    nmid=nmid,
                    best_keyword=best_keyword,
                    min_bids_map=min_bids_map,
                    current_bids_map=current_bids_map,
                    max_bid=max_bid,
                    target_position=target_position,
                    bidder_step=bidder_step
                )
                
                if new_bid is not None:
                    bid_updates.append({"nm": nmid, "cpm": new_bid})

            # Update bids if we have any
            if bid_updates:
                await self.update_bids(search_adv_id, bid_updates)
                logger.debug(f"Updated {len(bid_updates)} bids for adv {search_adv_id}")
            else:
                logger.debug(f"No bid updates needed for adv {search_adv_id}")
                
        except Exception as e:
            logger.critical(f"Critical error processing adv {search_adv_id}: {e}")
            raise

    async def _calculate_new_bid_for_nmid(
        self,
        nmid: int,
        best_keyword: CalculatedKeyword,
        min_bids_map: Dict[int, int],
        current_bids_map: Dict[int, int],
        max_bid: int,
        target_position: int,
        bidder_step: int
    ) -> Optional[int]:
        """Calculate new bid for a single nmid.
        
        Args:
            nmid: Product ID
            best_keyword: Best keyword for the campaign
            min_bids_map: Mapping of nmid to minimum bid
            current_bids_map: Mapping of nmid to current bid
            max_bid: Maximum allowed bid
            target_position: Target position
            bidder_step: Bidder step
            
        Returns:
            New bid value or None if no update needed
        """
        try:
            # Get position from Redis
            position = await redis_manager.get_keyword_position(best_keyword.text, nmid)
            if not position or position.position in {0, None}:
                logger.debug(f"Skip: invalid position for nmid {nmid}")
                return None

            # Get bid values
            min_bid = min_bids_map.get(nmid, 0)
            current_bid = current_bids_map.get(nmid, 0)
            
            if current_bid == 0:
                logger.debug(f"No current bid for nmid {nmid}, starting from 0")

            # Calculate new bid
            params = BidCalculationParams(
                current_bid=current_bid,
                min_bid=min_bid,
                max_bid=max_bid,
                current_position=position.position,
                target_position=target_position,
                bidder_step=bidder_step,
            )
            
            new_bid = self._bid_calculator.calculate_new_bid(params)
            
            if new_bid is None or new_bid == current_bid:
                logger.debug(f"Skip: new bid unchanged for nmid {nmid}")
                return None
                
            return int(new_bid)
            
        except Exception as e:
            logger.critical(f"Critical error calculating bid for nmid {nmid}: {e}")
            raise
