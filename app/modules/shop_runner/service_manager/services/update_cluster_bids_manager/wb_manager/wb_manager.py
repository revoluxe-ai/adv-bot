"""Чтение и запись min_bids в Redis (v2) для cluster bids и warmup.

Cache-only чтение: ``read_min_bids_cache_only`` / ``get_min_bids_cache_only``.
При miss ячейки — ``logger.warning`` (``min_bids cache miss``), не ERROR: miss
ожидаем до ``preload_min_bids_cache_miss`` или прогрева snapshot. ERROR — только
сбои WB refresh (``refresh_min_bids_cache_miss``). См. ``docks/snapshot_data_updater.md``.
"""

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
from app.core.mp.wb.min_bid_defaults import apply_min_bid_defaults_for_advs
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
from app.core.redis_manager_v2.redis_client import RedisClient
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
    @staticmethod
    async def read_min_bids_cache_only(
        advs: list[ComplexAdv],
        redis_client_wrapper: RedisClient,
        *,
        shop_id: str,
        context: str = "",
    ) -> AdvMinNmidsBids:
        """Чтение min_bids v2 из Redis без ``WBBaseManager.wb_manager_hub`` (snapshot/DI-free path).

        При miss ячейки — ``logger.warning`` (ожидаемо до ``preload_min_bids_cache_miss`` /
        snapshot). ERROR оставлен для ``refresh_min_bids_cache*`` (сбой WB). Ops: перенести
        алерты с ERROR ``min_bids cache miss`` на WARNING + подстроку (см. docks).
        """
        full_command = dto_to_command(advs)
        cache_manager = MinBidsCacheManager(redis_client_wrapper)
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
                    logger.warning(
                        "min_bids cache miss shop_id=%s context=%s adv_id=%s "
                        "placement=%s nmid=%s",
                        shop_id,
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

    async def _refresh_one_command_item_for_miss_cache(
        self,
        item: GetMinBidsCommandItem,
        miss_set: set[MinBidsV2Cell],
    ) -> int:
        """Один WB command_item → сразу запись в Redis (как refresh_min_bids_cache).

        Раньше все items ждали один общий ``await`` на весь список HTTP: до конца цикла
        адаптера в Redis ничего не попадало; при отмене/рестарте после пары запросов
        оставались те же cache miss.
        """
        wb_data = self.wb_manager_hub.wb_data_manager
        cache_manager = MinBidsCacheManager(self.wb_manager_hub.redis_client_wrapper)
        sub = GetMinBidsCommand(items=[item])
        try:
            per_item = await wb_data.get_min_bids_per_command_item(sub)
        except Exception as exc:
            return await self._split_min_bids_items_on_failure(
                [item], miss_set, exc=exc
            )

        if per_item is None:
            return await self._split_min_bids_items_on_failure(
                [item], miss_set, exc=None
            )

        fresh = per_item[0]
        batch = _min_bids_cache_entries_for_item_miss_only(item, fresh, miss_set)
        if not batch:
            return 0
        await cache_manager.set_min_bids_v2_batch(batch)
        return len(batch)

    async def _refresh_min_bids_command_items_with_split(
        self,
        items: list[GetMinBidsCommandItem],
        miss_set: set[MinBidsV2Cell],
    ) -> int:
        """По одному command_item: запрос WB и немедленная запись; при ошибке — split по nmids."""
        if not items:
            return 0
        written = 0
        for item in items:
            written += await self._refresh_one_command_item_for_miss_cache(
                item, miss_set
            )
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
            )
        else:
            logger.error(
                "refresh_min_bids_cache_miss: WB get_min_bids_per_command_item returned None "
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

        По одному ``GetMinBidsCommandItem`` (сгруппированные miss): после каждого ответа WB
        сразу пишем в Redis. При ошибке / ``None`` — split по ``nm_ids`` (см.
        ``_split_min_bids_items_on_failure``).
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
        apply_defaults: bool = True,
    ) -> AdvMinNmidsBids:
        """Только Redis v2; при miss — warning в лог.

        ``apply_defaults=True`` (по умолчанию): пропущенные ячейки заполняются
        ``MIN_BID_*_DEFAULT`` для расчётов/UI. ``False`` — raw cache (backfill-проверки).

        См. ``read_min_bids_cache_only``: miss штатны до фоновой догрузки; алерты по
        ``min_bids cache miss`` — уровень WARNING, не ERROR.
        """
        return await self._get_min_bids_cache_only_impl(
            advs,
            context=context,
            apply_defaults=apply_defaults,
        )

    async def _get_min_bids_cache_only_impl(
        self,
        advs: list[ComplexAdv],
        *,
        context: str,
        apply_defaults: bool = True,
    ) -> AdvMinNmidsBids:
        raw = await WBManager.read_min_bids_cache_only(
            advs,
            self.wb_manager_hub.redis_client_wrapper,
            shop_id=self._shop_id,
            context=context,
        )
        if not apply_defaults:
            return raw
        return apply_min_bid_defaults_for_advs(raw, advs, context=context)

    async def get_min_bids(
        self,
        advs: list[ComplexAdv],
        cache_possible: bool,
        *,
        apply_defaults: bool = True,
    ) -> AdvMinNmidsBids:
        """cache_possible=True: только кеш. cache_possible=False: прямой запрос к WB API."""

        if cache_possible:
            return await self.get_min_bids_cache_only(
                advs,
                context="get_min_bids_cache_possible",
                apply_defaults=apply_defaults,
            )

        min_bids = await self.wb_manager_hub.wb_data_manager.get_min_bids(advs)
        if min_bids is None:
            raise ClusterBidsUpdateError(
                "Ошибка получения минимальных ставок для кампании"
            )
        if not apply_defaults:
            return min_bids
        return apply_min_bid_defaults_for_advs(
            min_bids,
            advs,
            context="get_min_bids_wb_api",
        )
