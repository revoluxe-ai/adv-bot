"""Redis snapshot provider: Stub и Live (read-only legacy cache).

Читает существующие ключи (не меняет формат):
- ``calculated_keywords:{adv_id}`` — hash keywords;
- ``min_bids:v2:adv:{id}:pt:{placement}:nmid:{nmid}`` — batch mget на shop.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_min_bids_cache_manager import (
    MinBidsAdvPlacementCacheMixin,
    MinBidsV2Cell,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.snapshot_data_updater.dto import (
    AdvSettingsSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    MinBidCellDTO,
    MinBidsSnapshotDTO,
)
from app.snapshot_data_updater.mappers.keyword_mapper import (
    calculated_keywords_to_snapshots,
)

logger = logging.getLogger(__name__)


class StubRedisSnapshotProvider:
    """Фикстуры keywords/min_bids или cache miss (stub stack)."""

    def __init__(
        self,
        *,
        keywords_by_adv: dict[int, list[CalculatedKeywordSnapshotDTO]] | None = None,
        min_bids_by_adv: dict[int, MinBidsSnapshotDTO] | None = None,
        default_cache_hit: bool = False,
    ) -> None:
        self._keywords = keywords_by_adv or {}
        self._min_bids = min_bids_by_adv or {}
        self._default_cache_hit = default_cache_hit

    async def fetch_keywords(
        self, adv_id: int
    ) -> list[CalculatedKeywordSnapshotDTO]:
        if adv_id in self._keywords:
            return list(self._keywords[adv_id])
        if self._default_cache_hit:
            return [
                CalculatedKeywordSnapshotDTO(
                    text="stub-keyword",
                    adv_id=adv_id,
                    status=KeywordStatus.GOOD,
                    rating=1.0,
                    resolved_cpm=100.0,
                )
            ]
        return []

    async def fetch_min_bids(self, adv_id: int) -> MinBidsSnapshotDTO | None:
        if adv_id in self._min_bids:
            return self._min_bids[adv_id]
        if self._default_cache_hit:
            return MinBidsSnapshotDTO(
                adv_id=adv_id,
                search_by_nmid={12345: 50},
                cache_hit=True,
                coverage_ratio=1.0,
                requested_cells=1,
                hit_cells=1,
            )
        return None

    async def fetch_min_bids_for_settings(
        self, settings_list: Sequence[AdvSettingsSnapshotDTO]
    ) -> dict[int, MinBidsSnapshotDTO]:
        out: dict[int, MinBidsSnapshotDTO] = {}
        for s in settings_list:
            mb = await self.fetch_min_bids(s.adv_id)
            if mb is not None:
                out[s.adv_id] = mb
        return out


def _cells_for_settings(settings: AdvSettingsSnapshotDTO) -> list[MinBidsV2Cell]:
    """Все ожидаемые v2-ячейки для одной РК (auto + search × nmids)."""
    cells: list[MinBidsV2Cell] = []
    nmids = settings.nmids or ([settings.nm_id] if settings.nm_id else [])
    for nmid in nmids:
        if nmid is None:
            continue
        cells.append((settings.adv_id, AdvPlacementType.AUTO_ADV, int(nmid)))
        if settings.search_adv_id is not None:
            cells.append(
                (settings.search_adv_id, AdvPlacementType.SEARCH_ADV, int(nmid))
            )
    return cells


class RedisSnapshotProviderLive:
    """Read-only Redis: keywords hash + batch min_bids mget."""

    def __init__(
        self,
        *,
        keywords_cache: RedisCalculatedKeywordsCacheManager | None = None,
    ) -> None:
        self._keywords_cache = keywords_cache or RedisCalculatedKeywordsCacheManager()

    async def fetch_keywords(
        self, adv_id: int
    ) -> list[CalculatedKeywordSnapshotDTO]:
        """Чтение legacy hash без проверки ``SNAPSHOT_CACHE_MAX_AGE_SEC`` (сбор snapshot)."""
        cached = await self._keywords_cache.get_all_calculated_keywords_for_adv(adv_id)
        if cached is None:
            return []
        return calculated_keywords_to_snapshots(cached)

    async def fetch_min_bids(self, adv_id: int) -> MinBidsSnapshotDTO | None:
        return None

    async def fetch_min_bids_for_settings(
        self, settings_list: Sequence[AdvSettingsSnapshotDTO]
    ) -> dict[int, MinBidsSnapshotDTO]:
        """Один mget на все ячейки магазина — основной batch path collector."""
        cells: list[MinBidsV2Cell] = []
        cells_by_adv: dict[int, list[MinBidsV2Cell]] = {}
        for settings in settings_list:
            adv_cells = _cells_for_settings(settings)
            cells.extend(adv_cells)
            cells_by_adv[settings.adv_id] = adv_cells

        keys = [
            MinBidsAdvPlacementCacheMixin.min_bids_v2_key(a, p, n) for a, p, n in cells
        ]
        raw_list = await self._keywords_cache.client.mget(keys)
        cached_map: dict[MinBidsV2Cell, int] = {}
        for cell, raw in zip(cells, raw_list, strict=True):
            if not raw:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                data = json.loads(raw)
                cached_map[cell] = int(data["cpm"])
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                logger.debug(
                    "min_bids v2 skip malformed cell adv=%s placement=%s nmid=%s",
                    cell[0],
                    cell[1],
                    cell[2],
                )
                continue

        result: dict[int, MinBidsSnapshotDTO] = {}
        for settings in settings_list:
            adv_cells = cells_by_adv.get(settings.adv_id, [])
            search_by_nmid: dict[int, int] = {}
            auto_by_nmid: dict[int, int] = {}
            missing: list[MinBidCellDTO] = []
            hits = 0
            for cell in adv_cells:
                adv_id_cell, placement, nmid = cell
                cpm = cached_map.get(cell)
                if cpm is None:
                    missing.append(
                        MinBidCellDTO(
                            adv_id=adv_id_cell,
                            placement=placement.value,
                            nmid=nmid,
                        )
                    )
                    continue
                hits += 1
                if placement == AdvPlacementType.SEARCH_ADV:
                    search_by_nmid[nmid] = cpm
                else:
                    auto_by_nmid[nmid] = cpm
            requested = len(adv_cells)
            coverage = hits / requested if requested else 0.0
            result[settings.adv_id] = MinBidsSnapshotDTO(
                adv_id=settings.adv_id,
                search_by_nmid=search_by_nmid,
                auto_by_nmid=auto_by_nmid,
                requested_cells=requested,
                hit_cells=hits,
                missing_cells=missing,
                coverage_ratio=coverage,
                cache_hit=hits > 0 and not missing,
            )
        return result
