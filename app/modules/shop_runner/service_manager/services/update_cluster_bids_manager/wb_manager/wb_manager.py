import logging

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.wb_base_manager import WBBaseManager
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.excs import ClusterBidsUpdateError
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    UpdateBidsCommand,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_min_bids_cache_manager import (
    MinBidsCacheManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv


logger = logging.getLogger(__name__)



class WBManager(WBBaseManager):

    async def get_current_bids(self, advs: list[ComplexAdv]) -> list[NormqueryBidDTO]:
        wb_manager_hub = self.wb_manager_hub
        bids: list[NormqueryBidDTO] | None = await wb_manager_hub.wb_data_manager.get_current_bids_for_advs(advs)
        if bids is None:
            raise ValueError('Not given min bids data')
        return bids

    async def set_new_cluster_bids(self, update_bids_command: UpdateBidsCommand):
        await self.wb_manager_hub.wb_modifier.set_cluster_bids_for_adv(update_bids_command)


    async def get_min_bids(self, advs: list[ComplexAdv], cache_possible: bool) -> AdvMinNmidsBids:
        """Получить минимальные ставки CPM (auto/search) для переданных рекламных кампаний."""

        all_nmids: set[int] = set()
        for adv in advs:
            all_nmids.update(adv.nmids)

        nmids_list = list(all_nmids)

        redis_client = self.wb_manager_hub.redis_client_wrapper
        cache_manager = MinBidsCacheManager(redis_client)
        if cache_possible:
            cached_data = await cache_manager.get_min_bids_for_nmids(nmids_list)
            if len(cached_data) == len(all_nmids):
                logger.info("Min bids cache HIT for %s/%s nmids", len(cached_data), len(all_nmids))
                auto_dict = {nmid: cpms[0] for nmid, cpms in cached_data.items()}
                search_dict = {nmid: cpms[1] for nmid, cpms in cached_data.items()}
                return AdvMinNmidsBids(auto=auto_dict, search=search_dict)

            logger.info(
                "Min bids cache MISS (%s/%s cached), fetching from API",
                len(cached_data),
                len(all_nmids),
            )

        min_bids = await self.wb_manager_hub.wb_data_manager.get_min_bids(advs)
        if min_bids is None:
            raise ClusterBidsUpdateError("Ошибка получения минимальных ставок для кампании")

        cached_count = 0
        for nmid in all_nmids:
            auto_cpm = min_bids.auto.get(nmid, 0)
            search_cpm = min_bids.search.get(nmid, 0)
            await cache_manager.set_min_bid_for_nmid(nmid, auto_cpm, search_cpm)
            cached_count += 1

        logger.info("Cached min bids for %s nmids", cached_count)
        return min_bids








