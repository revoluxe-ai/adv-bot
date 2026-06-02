"""``RedisAdvDataSnapshotStore`` — запись/чтение snapshot в Redis.

Режимы
------
- ``no_op=True`` (default для stub): только debug-лог, без Redis I/O.
- ``no_op=False`` (live): JSON в ключи ``adv_snapshot:v1:...`` с TTL.

Consumers читают через ``SnapshotReader`` / adapters, не напрямую из legacy keys.
"""

from __future__ import annotations

import json
import logging

from app.snapshot_data_updater.config import DEFAULT_CONFIG
from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    ShopAdvSnapshotBatchDTO,
)
from app.snapshot_data_updater.keys import adv_snapshot_key, shop_batch_key

logger = logging.getLogger(__name__)


class RedisAdvDataSnapshotStore:
    """Реализация ``AdvDataSnapshotStore`` на Redis."""

    def __init__(
        self,
        *,
        redis_client: object | None = None,
        ttl_sec: int | None = None,
        no_op: bool = True,
    ) -> None:
        """Args:
            redis_client: asyncio Redis; по умолчанию из ``RedisCalculatedKeywordsCacheManager``.
            ttl_sec: EX для ключей; по умолчанию ``DEFAULT_CONFIG.snapshot_ttl_sec``.
            no_op: stub path — не писать в Redis.
        """
        self._no_op = no_op
        self._ttl_sec = ttl_sec if ttl_sec is not None else DEFAULT_CONFIG.snapshot_ttl_sec
        if redis_client is not None:
            self._client = redis_client
        else:
            from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
                RedisCalculatedKeywordsCacheManager,
            )

            self._client = RedisCalculatedKeywordsCacheManager().client

    async def save(self, batch: ShopAdvSnapshotBatchDTO) -> None:
        """Сохраняет batch + per-adv ключи.

        Side effects:
            Redis SET с TTL (только при ``no_op=False``).
        """
        if self._no_op:
            logger.debug(
                "RedisAdvDataSnapshotStore.save (no-op): shop_id=%s snapshots=%d",
                batch.shop_id,
                len(batch.snapshots),
            )
            return
        payload = batch.model_dump_json()
        await self._client.set(
            shop_batch_key(batch.shop_id),
            payload,
            ex=self._ttl_sec,
        )
        for snap in batch.snapshots:
            await self._client.set(
                adv_snapshot_key(batch.shop_id, snap.adv_id),
                snap.model_dump_json(),
                ex=self._ttl_sec,
            )
        logger.debug(
            "RedisAdvDataSnapshotStore.save shop_id=%s snapshots=%d",
            batch.shop_id,
            len(batch.snapshots),
        )

    async def load_shop_latest(
        self, shop_id: str
    ) -> ShopAdvSnapshotBatchDTO | None:
        """Читает ``adv_snapshot:v1:shop:{shop_id}:latest``."""
        if self._no_op:
            return None
        raw = await self._client.get(shop_batch_key(shop_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            return ShopAdvSnapshotBatchDTO.model_validate(json.loads(raw))
        except (TypeError, ValueError) as exc:
            logger.warning(
                "RedisAdvDataSnapshotStore.load_shop_latest invalid payload: %s",
                exc,
            )
            return None

    async def load_adv_snapshot(
        self, shop_id: str, adv_id: int
    ) -> AdvDataSnapshotDTO | None:
        """Читает снимок одной РК для consumer adapter."""
        if self._no_op:
            return None
        raw = await self._client.get(adv_snapshot_key(shop_id, adv_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            return AdvDataSnapshotDTO.model_validate(json.loads(raw))
        except (TypeError, ValueError) as exc:
            logger.warning(
                "RedisAdvDataSnapshotStore.load_adv_snapshot invalid: shop=%s adv=%s %s",
                shop_id,
                adv_id,
                exc,
            )
            return None
