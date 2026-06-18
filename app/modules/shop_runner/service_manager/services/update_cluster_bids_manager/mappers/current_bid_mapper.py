from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from .adv_id_item_map import AdvIdItemCalculateData


class CurrentBidMapper:
    def __init__(self, current_bids: list[NormqueryBidDTO]):
        self._bid_index: dict[tuple[int, int, str], int] = {
            (bid.advert_id, bid.nm_id, bid.norm_query): bid.bid for bid in current_bids
        }

    def get_current_bid(self, item_map: AdvIdItemCalculateData) -> int | None:
        key = (item_map.search_adv_id, item_map.nmid, item_map.cluster)
        return self._bid_index.get(key)
