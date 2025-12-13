
from .adv_id_item_map import AdvIdItemCalculateData

from ..dto.bidder_update_data import BidderUpdateData
from .current_bid_mapper import CurrentBidMapper
from .current_position_mapper import CurrentPositionMapper
from .min_bids_mapper import MinBidsMapper

class Mapper:
    def __init__(self, bidder_update_data: BidderUpdateData) -> None:

        data = bidder_update_data
        cluster_bids = data.cluster_bids or []
        self._current_bid_mapper = CurrentBidMapper(cluster_bids)
        self._current_position_mapper = CurrentPositionMapper()
        self._min_bids_mapper = MinBidsMapper(data.min_bids)

    def get_current_bid(self, map_data: AdvIdItemCalculateData) -> int | None:
        return self._current_bid_mapper.get_current_bid(map_data)


    def get_current_position(self, map_data: AdvIdItemCalculateData) -> float:
        return self._current_position_mapper.get_current_position(map_data)

    @staticmethod
    def get_target_position(map_data: AdvIdItemCalculateData) -> int:
        return map_data.target_position

    def get_min_bid(self, map_data: AdvIdItemCalculateData) -> int | None:
        return self._min_bids_mapper.get_min_bid(map_data)







