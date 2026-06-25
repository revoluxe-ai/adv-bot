from app.core.mp.wb.dto import AdvMinNmidsBids
from app.core.mp.wb.min_bid_defaults import resolve_search_min_bid_rub
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
        if nmid not in self._min_bids_map:
            default_rub = resolve_search_min_bid_rub(nmid, None)
            logger.warning(
                'Не найдена минимальная ставка для %s, используем default_rub=%s',
                nmid,
                default_rub,
            )
            return default_rub
        min_bid = self._min_bids_map[nmid]
        if int(min_bid) <= 0:
            default_rub = resolve_search_min_bid_rub(nmid, None)
            logger.warning(
                'Невалидная минимальная ставка для %s, используем default_rub=%s',
                nmid,
                default_rub,
            )
            return default_rub
        return min_bid