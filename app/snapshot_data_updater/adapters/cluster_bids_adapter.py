"""Adapter входа ``update_cluster_bids`` из snapshot (shadow / read + fallback).

Не затрагивает ``_apply_command`` / ``wb_modifier`` — только чтение keywords
(и в будущем cluster_texts) до расчёта карт.

Read cutover: при usable snapshot вызывается legacy ``get_keywords(cache_only=True)``
— данные уже в Redis после warmup updater'а.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.snapshot_data_updater.adapters.snapshot_reader import SnapshotReader
from app.snapshot_data_updater.config import DEFAULT_CONFIG, SnapshotUpdaterConfig
from app.snapshot_data_updater.dto import AdvDataSnapshotDTO

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )

logger = logging.getLogger(__name__)


class ClusterBidsSnapshotAdapter:
    """Shadow-compare и read path для keywords (и cluster_texts)."""

    def __init__(
        self,
        reader: SnapshotReader | None = None,
        config: SnapshotUpdaterConfig | None = None,
    ) -> None:
        self._reader = reader or SnapshotReader()
        self._config = config or DEFAULT_CONFIG

    async def load_snapshot(
        self, shop_id: str, adv_id: int
    ) -> AdvDataSnapshotDTO | None:
        return await self._reader.get_adv_snapshot(shop_id, adv_id)

    async def get_keywords_for_adv(
        self,
        complex_adv: ComplexAdv,
        *,
        fallback_getter: object | None = None,
    ) -> list[CalculatedKeyword] | None:
        """Keywords с учётом флагов ``SNAPSHOT_CLUSTER_BIDS_*``.

        Shadow: лог расхождения count snapshot vs legacy.
        Read: при usable snapshot — ``cache_only`` (Redis после warmup).
        Иначе — полный fallback на ``adv.get_keywords``.
        """
        shop_id = complex_adv.shop_id or ""
        snapshot = await self.load_snapshot(shop_id, complex_adv.adv_id)

        if self._config.cluster_bids_shadow_compare and snapshot is not None:
            await self._shadow_compare_keywords(complex_adv, snapshot, fallback_getter)

        if (
            self._config.cluster_bids_read_from_snapshot
            and self._reader.is_snapshot_usable(snapshot)
        ):
            getter = fallback_getter or complex_adv.get_keywords
            return await getter(cache_only=True, allow_miss=True)

        if fallback_getter is not None and callable(fallback_getter):
            return await fallback_getter(cache_only=True, allow_miss=True)
        return await complex_adv.get_keywords(cache_only=True, allow_miss=True)

    async def get_cluster_texts_for_adv(
        self,
        complex_adv: ComplexAdv,
        *,
        fallback_texts: set[str],
    ) -> set[str]:
        """Cluster texts из snapshot или fallback (CH path менеджера)."""
        shop_id = complex_adv.shop_id or ""
        snapshot = await self.load_snapshot(shop_id, complex_adv.adv_id)
        if (
            self._config.cluster_bids_read_from_snapshot
            and snapshot is not None
            and snapshot.cluster_texts is not None
            and snapshot.cluster_texts.texts
        ):
            return set(snapshot.cluster_texts.texts)
        return fallback_texts

    async def _shadow_compare_keywords(
        self,
        complex_adv: ComplexAdv,
        snapshot: AdvDataSnapshotDTO,
        fallback_getter: object | None,
    ) -> None:
        old_kw: list[CalculatedKeyword] | None = None
        if fallback_getter is not None and callable(fallback_getter):
            old_kw = await fallback_getter(cache_only=True, allow_miss=True)
        else:
            old_kw = await complex_adv.get_keywords(cache_only=True, allow_miss=True)
        snap_count = len(snapshot.keywords)
        old_count = len(old_kw) if old_kw else 0
        if snap_count != old_count:
            logger.info(
                "snapshot shadow keywords mismatch adv_id=%s snap=%d old=%d",
                complex_adv.adv_id,
                snap_count,
                old_count,
            )
