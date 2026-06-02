"""Adapter для пути ``get_wb_advs_dto`` / V3 (shadow-логи, будущий read cutover).

``WBShopDataManager._collect_keywords`` читает keywords только из Redis (``cache_only``);
при miss — ``KeywordsCacheMissError``.
"""

from __future__ import annotations

import logging

from app.snapshot_data_updater.adapters.snapshot_reader import SnapshotReader
from app.snapshot_data_updater.config import (
    SnapshotUpdaterConfig,
    resolve_snapshot_config,
)
from app.snapshot_data_updater.dto import AdvDataSnapshotDTO

logger = logging.getLogger(__name__)


class WBAdvDtoSnapshotAdapter:
    """Вспомогательный adapter для WBAdvDTO pipeline."""

    def __init__(
        self,
        reader: SnapshotReader | None = None,
        config: SnapshotUpdaterConfig | None = None,
    ) -> None:
        self._reader = reader or SnapshotReader()
        self._config = resolve_snapshot_config(config)

    async def load_snapshot(
        self, shop_id: str, adv_id: int
    ) -> AdvDataSnapshotDTO | None:
        return await self._reader.get_adv_snapshot(shop_id, adv_id)

    async def shadow_log_keywords_delta(
        self,
        shop_id: str,
        adv_id: int,
        *,
        legacy_count: int,
    ) -> None:
        """Shadow: сравнение числа keywords snapshot vs legacy после load."""
        if not self._config.wb_adv_dto_shadow_compare:
            return
        snapshot = await self._reader.get_adv_snapshot(
            shop_id, adv_id, enforce_stale=False
        )
        if snapshot is None:
            return
        snap_count = len(snapshot.keywords)
        if snap_count != legacy_count:
            logger.info(
                "wb_adv_dto shadow keywords adv_id=%s snap=%d legacy=%d",
                adv_id,
                snap_count,
                legacy_count,
            )
