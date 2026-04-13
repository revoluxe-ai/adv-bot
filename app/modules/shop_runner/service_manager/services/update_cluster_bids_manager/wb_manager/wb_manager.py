import logging

from app.core.mp.wb.api.adapter.promotion_client.min_bids.command import (
    GetMinBidsCommand,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.api.domain_managers.promotion.methods.get_min_bids.convertor import (
    dto_to_command,
)
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.core.mp.wb.wb_base_manager import WBBaseManager
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.excs import (
    ClusterBidsUpdateError,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    UpdateBidsCommand,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_min_bids_cache_manager import (
    MinBidsCacheManager,
    MinBidsV2Cell,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


logger = logging.getLogger(__name__)


class WBManager(WBBaseManager):
    async def get_current_bids(self, advs: list[ComplexAdv]) -> list[NormqueryBidDTO]:
        wb_manager_hub = self.wb_manager_hub
        bids: list[NormqueryBidDTO] | None = (
            await wb_manager_hub.wb_data_manager.get_current_bids_for_advs(advs)
        )
        if bids is None:
            raise ValueError("Not given min bids data")
        return bids

    async def set_new_cluster_bids(self, update_bids_command: UpdateBidsCommand):
        await self.wb_manager_hub.wb_modifier.set_cluster_bids_for_adv(
            update_bids_command
        )

    async def refresh_min_bids_cache(self, advs: list[ComplexAdv]) -> None:
        """Загрузить минимальные ставки из WB API и записать в Redis v2 (фоновая корутина)."""
        if not advs:
            return
        full_command = dto_to_command(advs)
        wb_data = self.wb_manager_hub.wb_data_manager
        cache_manager = MinBidsCacheManager(self.wb_manager_hub.redis_client_wrapper)
        to_write: list[tuple[int, AdvPlacementType, int, int]] = []

        if full_command.items:
            fresh = await wb_data.get_min_bids_for_command(full_command)
            if fresh is None:
                logger.error(
                    "refresh_min_bids_cache: WB get_min_bids_for_command returned None "
                    "shop_id=%s",
                    self._shop_id,
                )
                return
            for item in full_command.items:
                for nmid in item.nmids:
                    if item.placement_type == AdvPlacementType.AUTO_ADV:
                        cpm = fresh.auto.get(nmid)
                    elif item.placement_type == AdvPlacementType.SEARCH_ADV:
                        cpm = fresh.search.get(nmid)
                    else:
                        continue
                    if cpm is not None:
                        to_write.append(
                            (item.adv_id, item.placement_type, nmid, int(cpm))
                        )
        else:
            fresh = await wb_data.get_min_bids(advs)
            if fresh is None:
                logger.error(
                    "refresh_min_bids_cache: WB get_min_bids returned None shop_id=%s",
                    self._shop_id,
                )
                return
            for adv in advs:
                for nmid in adv.nmids:
                    a = fresh.auto.get(nmid)
                    if a is not None:
                        to_write.append(
                            (
                                adv.auto_adv_id,
                                AdvPlacementType.AUTO_ADV,
                                nmid,
                                int(a),
                            )
                        )
                    if adv.search_adv_id is not None:
                        s = fresh.search.get(nmid)
                        if s is not None:
                            to_write.append(
                                (
                                    adv.search_adv_id,
                                    AdvPlacementType.SEARCH_ADV,
                                    nmid,
                                    int(s),
                                )
                            )

        await cache_manager.set_min_bids_v2_batch(to_write)
        logger.info(
            "refresh_min_bids_cache shop_id=%s cells_written=%s",
            self._shop_id,
            len(to_write),
        )

    async def get_min_bids_cache_only(
        self,
        advs: list[ComplexAdv],
        *,
        context: str = "",
    ) -> AdvMinNmidsBids:
        """Только Redis v2; при miss — error в лог, ячейка не попадает в результат."""
        full_command = dto_to_command(advs)
        cache_manager = MinBidsCacheManager(self.wb_manager_hub.redis_client_wrapper)
        hits_auto: dict[int, int] = {}
        hits_search: dict[int, int] = {}

        if not full_command.items:
            return AdvMinNmidsBids(auto=hits_auto, search=hits_search)

        cells: list[MinBidsV2Cell] = []
        for item in full_command.items:
            for nmid in item.nmids:
                cells.append((item.adv_id, item.placement_type, nmid))

        cached_map = await cache_manager.get_min_bids_v2_batch(cells)

        for item in full_command.items:
            for nmid in item.nmids:
                cell: MinBidsV2Cell = (item.adv_id, item.placement_type, nmid)
                cpm = cached_map.get(cell)
                if cpm is None:
                    logger.error(
                        "min_bids cache miss shop_id=%s context=%s adv_id=%s "
                        "placement=%s nmid=%s",
                        self._shop_id,
                        context,
                        item.adv_id,
                        item.placement_type.value,
                        nmid,
                    )
                    continue
                if item.placement_type == AdvPlacementType.AUTO_ADV:
                    hits_auto[nmid] = cpm
                elif item.placement_type == AdvPlacementType.SEARCH_ADV:
                    hits_search[nmid] = cpm

        return AdvMinNmidsBids(auto=hits_auto, search=hits_search)

    async def get_min_bids(
        self, advs: list[ComplexAdv], cache_possible: bool
    ) -> AdvMinNmidsBids:
        """cache_possible=True: только кеш. cache_possible=False: прямой запрос к WB API."""

        if cache_possible:
            return await self.get_min_bids_cache_only(
                advs, context="get_min_bids_cache_possible"
            )

        min_bids = await self.wb_manager_hub.wb_data_manager.get_min_bids(advs)
        if min_bids is None:
            raise ClusterBidsUpdateError(
                "Ошибка получения минимальных ставок для кампании"
            )
        return min_bids
