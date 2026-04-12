import logging

from app.core.mp.wb.api.adapter.promotion_client.min_bids.command import (
    GetMinBidsCommand,
    GetMinBidsCommandItem,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.api.domain_managers.promotion.methods.get_min_bids.convertor import (
    dto_to_command,
)
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
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

        if not cache_possible:
            min_bids = await self.wb_manager_hub.wb_data_manager.get_min_bids(advs)
            if min_bids is None:
                raise ClusterBidsUpdateError("Ошибка получения минимальных ставок для кампании")
            return min_bids

        full_command = dto_to_command(advs)
        if not full_command.items:
            min_bids = await self.wb_manager_hub.wb_data_manager.get_min_bids(advs)
            if min_bids is None:
                raise ClusterBidsUpdateError("Ошибка получения минимальных ставок для кампании")
            return min_bids

        redis_client = self.wb_manager_hub.redis_client_wrapper
        cache_manager = MinBidsCacheManager(redis_client)

        hits_auto: dict[int, int] = {}
        hits_search: dict[int, int] = {}
        reduced_items: list[GetMinBidsCommandItem] = []
        miss_adv_by_placement_nmid: dict[tuple[AdvPlacementType, int], int] = {}
        total_cells = 0
        hit_cells = 0

        for item in full_command.items:
            miss_nmids: list[int] = []
            for nmid in item.nmids:
                total_cells += 1
                cached_cpm = await cache_manager.get_min_bid_for_adv_placement_nmid(
                    item.adv_id,
                    item.placement_type,
                    nmid,
                )
                if cached_cpm is not None:
                    hit_cells += 1
                    if item.placement_type == AdvPlacementType.AUTO_ADV:
                        hits_auto[nmid] = cached_cpm
                    elif item.placement_type == AdvPlacementType.SEARCH_ADV:
                        hits_search[nmid] = cached_cpm
                    continue
                miss_nmids.append(nmid)
                key = (item.placement_type, nmid)
                prev = miss_adv_by_placement_nmid.get(key)
                if prev is not None and prev != item.adv_id:
                    logger.warning(
                        "min_bids cache miss map conflict: placement=%s nmid=%s "
                        "adv_id %s vs %s (using last)",
                        item.placement_type.value,
                        nmid,
                        prev,
                        item.adv_id,
                    )
                miss_adv_by_placement_nmid[key] = item.adv_id

            if miss_nmids:
                reduced_items.append(item.model_copy(update={"nmids": miss_nmids}))

        hits = AdvMinNmidsBids(auto=hits_auto, search=hits_search)

        if not reduced_items:
            logger.info(
                "Min bids cache full HIT: %s/%s cells (adv+placement+nmid)",
                hit_cells,
                total_cells,
            )
            return hits

        logger.info(
            "Min bids cache partial: %s/%s cells HIT, fetching misses via API",
            hit_cells,
            total_cells,
        )

        reduced_command = GetMinBidsCommand(items=reduced_items)
        fresh = await self.wb_manager_hub.wb_data_manager.get_min_bids_for_command(
            reduced_command
        )
        if fresh is None:
            raise ClusterBidsUpdateError("Ошибка получения минимальных ставок для кампании")

        merged = AdvMinNmidsBids(
            auto={**hits.auto, **fresh.auto},
            search={**hits.search, **fresh.search},
        )

        written = 0
        for nmid, cpm in fresh.auto.items():
            adv_id = miss_adv_by_placement_nmid.get((AdvPlacementType.AUTO_ADV, nmid))
            if adv_id is None:
                continue
            await cache_manager.set_min_bid_for_adv_placement_nmid(
                adv_id,
                AdvPlacementType.AUTO_ADV,
                nmid,
                cpm,
            )
            written += 1

        for nmid, cpm in fresh.search.items():
            adv_id = miss_adv_by_placement_nmid.get((AdvPlacementType.SEARCH_ADV, nmid))
            if adv_id is None:
                continue
            await cache_manager.set_min_bid_for_adv_placement_nmid(
                adv_id,
                AdvPlacementType.SEARCH_ADV,
                nmid,
                cpm,
            )
            written += 1

        logger.info("Cached min bids v2 for %s (adv+placement+nmid) cells", written)
        return merged








