"""``SnapshotReader`` — чтение ``AdvDataSnapshotDTO`` из Redis для consumer adapters."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.snapshot_data_updater.cache.redis_adv_data_snapshot_store import (
    RedisAdvDataSnapshotStore,
)
from app.snapshot_data_updater.cache_freshness import enforce_cache_max_age
from app.snapshot_data_updater.config import DEFAULT_CONFIG, SnapshotUpdaterConfig
from app.snapshot_data_updater.dto import AdvDataSnapshotDTO

logger = logging.getLogger(__name__)


class SnapshotReader:
    """Read-only доступ к сохранённым снимкам (новый Redis namespace)."""

    def __init__(
        self,
        store: RedisAdvDataSnapshotStore | None = None,
        config: SnapshotUpdaterConfig | None = None,
    ) -> None:
        self._store = store or RedisAdvDataSnapshotStore(no_op=False)
        self._config = config or DEFAULT_CONFIG

    async def get_adv_snapshot(
        self, shop_id: str, adv_id: int
    ) -> AdvDataSnapshotDTO | None:
        """Загружает per-adv ключ или None при miss / no_op store.

        Raises:
            CacheStaleError: snapshot старше ``SNAPSHOT_CACHE_MAX_AGE_SEC``.
        """
        snapshot = await self._store.load_adv_snapshot(shop_id, adv_id)
        if snapshot is not None:
            enforce_cache_max_age(
                snapshot.collected_at,
                self._config.cache_max_age_sec,
                context=f"snapshot shop_id={shop_id} adv_id={adv_id}",
                require_timestamp=True,
            )
        return snapshot

    def is_snapshot_usable(self, snapshot: AdvDataSnapshotDTO | None) -> bool:
        """Проверка для read cutover ``update_cluster_bids``.

        Условия: версия схемы, не истёк TTL, settings/keywords/min_bids complete.
        """
        if snapshot is None:
            return False
        if snapshot.schema_version != self._config.snapshot_schema_version:
            return False
        if snapshot.expires_at is not None:
            if datetime.now(tz=UTC) >= snapshot.expires_at:
                return False
        if self._config.cache_max_age_sec > 0:
            from app.snapshot_data_updater.cache_freshness import cache_age_sec

            age = cache_age_sec(snapshot.collected_at)
            if age > self._config.cache_max_age_sec:
                return False
        completeness = snapshot.section_completeness
        if not completeness.get("settings"):
            return False
        if not completeness.get("keywords"):
            return False
        kw = snapshot.diagnostics.keywords
        if not kw.keywords_cache_hit and kw.keywords_source in {
            "missing",
            "error",
        }:
            return False
        min_bids = snapshot.min_bids
        if min_bids is None or min_bids.coverage_ratio <= 0:
            return False
        return True
