"""Adapter входа ``update_cluster_bids`` из snapshot (shadow / read).

Не затрагивает ``_apply_command`` / ``wb_modifier`` — только чтение keywords
до расчёта карт. Источник keywords для shop-runner — strict Redis
(``adv.get_keywords``); miss → ``ShopRunnerKeywordsCacheMissError``.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from app.modules.shop_runner.required_data_miss import ShopRunnerKeywordsCacheMissError
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.snapshot_data_updater.adapters.snapshot_reader import SnapshotReader
from app.snapshot_data_updater.config import (
    SnapshotUpdaterConfig,
    resolve_snapshot_config,
)
from app.snapshot_data_updater.dto import AdvDataSnapshotDTO

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )

logger = logging.getLogger(__name__)

RedisKeywordsGetter = Callable[..., Awaitable[list[CalculatedKeyword]]]


class ClusterBidsSnapshotAdapter:
    """Shadow-compare и read path для keywords (и cluster_texts)."""

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
        """Загрузка snapshot для shadow/diagnostics — без ``enforce_stale``.

        Keywords cluster_bids всегда из strict Redis; stale JSON не должен ронять
        корутину (аналог ``WBAdvDtoSnapshotAdapter.shadow_log_keywords_delta``).
        """
        return await self._reader.get_adv_snapshot(
            shop_id, adv_id, enforce_stale=False
        )

    async def get_keywords_for_adv(
        self,
        complex_adv: ComplexAdv,
        *,
        redis_getter: RedisKeywordsGetter | None = None,
    ) -> list[CalculatedKeyword]:
        """Keywords для cluster_bids: strict Redis; shadow — сравнение с snapshot JSON.

        Args:
            complex_adv: РК shop-runner.
            redis_getter: обычно ``adv.get_keywords`` (strict cache).

        Raises:
            ShopRunnerKeywordsCacheMissError: нет hash в Redis.
        """
        shop_id = complex_adv.shop_id or ""
        snapshot = await self.load_snapshot(shop_id, complex_adv.adv_id)

        if self._config.cluster_bids_shadow_compare and snapshot is not None:
            await self._shadow_compare_keywords(complex_adv, snapshot, redis_getter)

        getter = redis_getter or complex_adv.get_keywords
        return await getter()

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
            and self._reader.is_snapshot_usable(snapshot)
            and snapshot.cluster_texts is not None
            and snapshot.cluster_texts.texts
        ):
            return set(snapshot.cluster_texts.texts)
        return fallback_texts

    async def _shadow_compare_keywords(
        self,
        complex_adv: ComplexAdv,
        snapshot: AdvDataSnapshotDTO,
        redis_getter: RedisKeywordsGetter | None,
    ) -> None:
        getter = redis_getter or complex_adv.get_keywords
        old_kw: list[CalculatedKeyword] | None = None
        try:
            old_kw = await getter()
        except ShopRunnerKeywordsCacheMissError:
            old_kw = None
        snap_count = len(snapshot.keywords)
        old_count = len(old_kw) if old_kw else 0
        if snap_count != old_count:
            logger.info(
                "snapshot shadow keywords mismatch adv_id=%s snap=%d old=%d",
                complex_adv.adv_id,
                snap_count,
                old_count,
            )
