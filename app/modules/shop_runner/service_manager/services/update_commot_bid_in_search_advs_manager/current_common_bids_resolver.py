"""Resolve current common bids: Redis (last set) first, then WB API, then None."""

from __future__ import annotations

from app.core.mp.wb.api.managers import WBDataManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_value_manager import (
    RedisCommonBidValueManager,
)


class CurrentCommonBidsResolver:
    """Resolves current common bids per search_adv: Redis first, then WB API."""

    def __init__(
        self,
        redis_common_bid_value_manager: RedisCommonBidValueManager,
        wb_data_manager: WBDataManager,
        wb_shop_data_manager: WBShopDataManager,
    ) -> None:
        self._redis = redis_common_bid_value_manager
        self._wb_data_manager = wb_data_manager
        self._wb_shop_data_manager = wb_shop_data_manager

    async def get_merged_bids(
        self, complex_advs: list[ComplexAdv]
    ) -> dict[int, dict[int, int]]:
        """
        Return dict[search_adv_id, dict[nmid, bid]] with Redis overriding API.
        Fallback: API; if neither has a value for nmid, it is omitted.
        """
        if not complex_advs:
            return {}
        api_bids_raw = await self._wb_data_manager.get_current_bids_for_advs(
            complex_advs
        )
        api_aggregated = self._wb_shop_data_manager.aggregate_bids(api_bids_raw)
        result: dict[int, dict[int, int]] = {}
        for adv in complex_advs:
            search_adv_id = adv.search_adv_id
            if search_adv_id is None:
                continue
            nmids = adv.nmids
            redis_bids = await self._redis.get_bids(search_adv_id, nmids)
            api_bids = api_aggregated.get(search_adv_id, {})
            merged: dict[int, int] = {}
            for nmid in nmids:
                bid = redis_bids.get(nmid)
                if bid is None:
                    bid = api_bids.get(nmid)
                if bid is not None:
                    merged[nmid] = bid
            result[search_adv_id] = merged
        return result
