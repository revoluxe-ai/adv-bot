import logging
from collections import defaultdict

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


def _min_bids_cache_entries_for_item(
    item: GetMinBidsCommandItem,
    fresh: AdvMinNmidsBids,
) -> list[tuple[int, AdvPlacementType, int, int]]:
    out: list[tuple[int, AdvPlacementType, int, int]] = []
    for nmid in item.nmids:
        if item.placement_type == AdvPlacementType.AUTO_ADV:
            cpm = fresh.auto.get(nmid)
        elif item.placement_type == AdvPlacementType.SEARCH_ADV:
            cpm = fresh.search.get(nmid)
        else:
            continue
        if cpm is not None:
            out.append((item.adv_id, item.placement_type, nmid, int(cpm)))
    return out


def _min_bids_cache_entries_for_item_miss_only(
    item: GetMinBidsCommandItem,
    fresh: AdvMinNmidsBids,
    miss_set: set[MinBidsV2Cell],
) -> list[tuple[int, AdvPlacementType, int, int]]:
    full = _min_bids_cache_entries_for_item(item, fresh)
    return [e for e in full if (e[0], e[1], e[2]) in miss_set]


def _miss_cells_count_by_adv_id(misses: list[MinBidsV2Cell]) -> dict[int, int]:
    """Число незакэшированных v2-ячеек min bids по id кампании WB (advert_id в ячейке)."""
    counts: dict[int, int] = defaultdict(int)
    for adv_id, _placement, _nmid in misses:
        counts[adv_id] += 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def _group_miss_cells_to_command_items(
    miss_cells: list[MinBidsV2Cell],
) -> list[GetMinBidsCommandItem]:
    grouped: dict[tuple[int, AdvPlacementType], set[int]] = defaultdict(set)
    for adv_id, placement, nmid in miss_cells:
        grouped[(adv_id, placement)].add(nmid)
    items: list[GetMinBidsCommandItem] = []
    for (adv_id, placement), nmids in sorted(
        grouped.items(), key=lambda x: (x[0][0], x[0][1].value)
    ):
        items.append(
            GetMinBidsCommandItem(
                adv_id=adv_id,
                nmids=sorted(nmids),
                placement_type=placement,
            )
        )
    return items


def _min_bids_cache_entries_for_adv(
    adv: ComplexAdv,
    fresh: AdvMinNmidsBids,
) -> list[tuple[int, AdvPlacementType, int, int]]:
    out: list[tuple[int, AdvPlacementType, int, int]] = []
    for nmid in adv.nmids:
        a = fresh.auto.get(nmid)
        if a is not None:
            out.append(
                (adv.auto_adv_id, AdvPlacementType.AUTO_ADV, nmid, int(a)),
            )
        if adv.search_adv_id is not None:
            s = fresh.search.get(nmid)
            if s is not None:
                out.append(
                    (
                        adv.search_adv_id,
                        AdvPlacementType.SEARCH_ADV,
                        nmid,
                        int(s),
                    )
                )
    return out


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
        """Загрузить минимальные ставки из WB API и записать в Redis v2 (фоновая корутина).

        Запросы к WB идут по одному command_item / одной РК; после каждого успешного
        ответа данные сразу пишутся в кеш, без ожидания остальных.
        """
        if not advs:
            return
        full_command = dto_to_command(advs)
        wb_data = self.wb_manager_hub.wb_data_manager
        cache_manager = MinBidsCacheManager(self.wb_manager_hub.redis_client_wrapper)
        cells_written = 0

        if full_command.items:
            for item in full_command.items:
                sub = GetMinBidsCommand(items=[item])
                fresh = await wb_data.get_min_bids_for_command(sub)
                if fresh is None:
                    logger.error(
                        "refresh_min_bids_cache: WB get_min_bids_for_command returned None "
                        "shop_id=%s adv_id=%s placement=%s",
                        self._shop_id,
                        item.adv_id,
                        item.placement_type.value,
                    )
                    continue
                batch = _min_bids_cache_entries_for_item(item, fresh)
                if batch:
                    await cache_manager.set_min_bids_v2_batch(batch)
                    cells_written += len(batch)
        else:
            for adv in advs:
                fresh = await wb_data.get_min_bids([adv])
                if fresh is None:
                    logger.error(
                        "refresh_min_bids_cache: WB get_min_bids returned None shop_id=%s "
                        "auto_adv_id=%s",
                        self._shop_id,
                        adv.auto_adv_id,
                    )
                    continue
                batch = _min_bids_cache_entries_for_adv(adv, fresh)
                if batch:
                    await cache_manager.set_min_bids_v2_batch(batch)
                    cells_written += len(batch)

        logger.info(
            "refresh_min_bids_cache shop_id=%s cells_written=%s",
            self._shop_id,
            cells_written,
        )

    @staticmethod
    def expected_min_bids_v2_cells_from_advs(advs: list[ComplexAdv]) -> list[MinBidsV2Cell]:
        """Все ожидаемые v2-ячейки для списка РК (как в dto_to_command)."""
        full_command = dto_to_command(advs)
        cells: list[MinBidsV2Cell] = []
        for item in full_command.items:
            for nmid in item.nmids:
                cells.append((item.adv_id, item.placement_type, nmid))
        return cells

    async def find_min_bids_cache_miss_cells(
        self,
        advs: list[ComplexAdv],
        *,
        emit_app_log: bool = True,
        log_label: str = "min_bids_cache_miss snapshot",
    ) -> list[MinBidsV2Cell]:
        """Ячейки, отсутствующие в Redis v2 (cache miss)."""
        cells = self.expected_min_bids_v2_cells_from_advs(advs)
        if not cells:
            return []
        cache_manager = MinBidsCacheManager(self.wb_manager_hub.redis_client_wrapper)
        cached_map = await cache_manager.get_min_bids_v2_batch(cells)
        misses = [c for c in cells if c not in cached_map]
        miss_by_adv = _miss_cells_count_by_adv_id(misses)
        if emit_app_log:
            logger.info(
                "%s shop_id=%s cells_expected=%s cells_cached=%s cells_missed=%s "
                "distinct_adverts_with_miss=%s miss_by_adv_id=%s",
                log_label,
                self._shop_id,
                len(cells),
                len(cached_map),
                len(misses),
                len(miss_by_adv),
                miss_by_adv,
            )
        return misses

    async def _refresh_min_bids_command_items_with_split(
        self,
        items: list[GetMinBidsCommandItem],
        miss_set: set[MinBidsV2Cell],
    ) -> int:
        """Запрос WB пачкой; при ошибке или None — binary split по items или nmids."""
        if not items:
            return 0
        wb_data = self.wb_manager_hub.wb_data_manager
        cache_manager = MinBidsCacheManager(self.wb_manager_hub.redis_client_wrapper)

        async def write_for_items(
            batch_items: list[GetMinBidsCommandItem],
            fresh: AdvMinNmidsBids,
        ) -> int:
            written = 0
            for item in batch_items:
                batch = _min_bids_cache_entries_for_item_miss_only(
                    item, fresh, miss_set
                )
                if batch:
                    await cache_manager.set_min_bids_v2_batch(batch)
                    written += len(batch)
            return written

        cmd = GetMinBidsCommand(items=items)
        fresh: AdvMinNmidsBids | None
        try:
            # Один доменный вызов с полным списком items; адаптер внутри обходит items
            # последовательно (отдельные HTTP на пару advert+placement). При успехе —
            # одна запись в Redis по всем items из ответа; при сбое — split ниже.
            fresh = await wb_data.get_min_bids_for_command(cmd)
        except Exception as exc:
            return await self._split_min_bids_items_on_failure(
                items, miss_set, exc=exc
            )

        if fresh is None:
            return await self._split_min_bids_items_on_failure(
                items, miss_set, exc=None
            )

        written = await write_for_items(items, fresh)
        return written

    async def _split_min_bids_items_on_failure(
        self,
        items: list[GetMinBidsCommandItem],
        miss_set: set[MinBidsV2Cell],
        *,
        exc: Exception | None,
    ) -> int:
        if not items:
            return 0

        if len(items) > 1:
            mid = len(items) // 2
            a = await self._refresh_min_bids_command_items_with_split(
                items[:mid], miss_set
            )
            b = await self._refresh_min_bids_command_items_with_split(
                items[mid:], miss_set
            )
            return a + b

        item = items[0]
        if len(item.nmids) > 1:
            mid_n = len(item.nmids) // 2
            left = GetMinBidsCommandItem(
                adv_id=item.adv_id,
                nmids=item.nmids[:mid_n],
                placement_type=item.placement_type,
            )
            right = GetMinBidsCommandItem(
                adv_id=item.adv_id,
                nmids=item.nmids[mid_n:],
                placement_type=item.placement_type,
            )
            a = await self._refresh_min_bids_command_items_with_split(
                [left], miss_set
            )
            b = await self._refresh_min_bids_command_items_with_split(
                [right], miss_set
            )
            return a + b

        nmid = item.nmids[0]
        if exc is not None:
            logger.error(
                "refresh_min_bids_cache_miss: WB request failed for single cell "
                "shop_id=%s adv_id=%s placement=%s nmid=%s: %s",
                self._shop_id,
                item.adv_id,
                item.placement_type.value,
                nmid,
                exc,
                exc_info=True,
            )
        else:
            logger.error(
                "refresh_min_bids_cache_miss: WB get_min_bids_for_command returned None "
                "shop_id=%s adv_id=%s placement=%s nmid=%s",
                self._shop_id,
                item.adv_id,
                item.placement_type.value,
                nmid,
            )
        return 0

    async def refresh_min_bids_cache_miss_cells(
        self,
        miss_cells: list[MinBidsV2Cell],
    ) -> int:
        """Догрузить только cache-miss ячейки.

        Сначала один ``GetMinBidsCommand`` по всем сгруппированным miss-items. Если ответ
        успешен — пишем в Redis miss-ячейки из ответа. Если исключение или ``None`` —
        бинарный split по items / nmids и повторные запросы, пока не изолируем проблемную
        связку (см. ``_split_min_bids_items_on_failure``).
        """
        if not miss_cells:
            return 0
        items = _group_miss_cells_to_command_items(miss_cells)
        miss_set = set(miss_cells)
        written = await self._refresh_min_bids_command_items_with_split(items, miss_set)
        return written

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
