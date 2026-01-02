from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.mappers.adv_id_item_map import \
    AdvIdItemCalculateData
import logging


logger = logging.getLogger(__name__)

class MinBidsMapper:
    def __init__(self, min_bids: AdvMinNmidsBids) -> None:
        search_min_bids = min_bids.search
        self._min_bids_map = search_min_bids


    def get_min_bid(self, map_data: AdvIdItemCalculateData) -> int | None:
        nmid = map_data.nmid
        if not nmid in self._min_bids_map:
            logger.error('Не найдена минимальная ставка для %s', nmid)
            return None
        min_bid = self._min_bids_map[nmid]
        return min_bid