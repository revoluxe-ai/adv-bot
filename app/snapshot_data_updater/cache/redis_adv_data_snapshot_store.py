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

from pydantic import ValidationError
from redis.asyncio import Redis

from app.snapshot_data_updater.config import get_snapshot_config
from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    ShopAdvSnapshotBatchDTO,
)
from app.snapshot_data_updater.keys import (
    adv_snapshot_key,
    shop_batch_key,
    shop_per_adv_snapshot_pattern,
)

logger = logging.getLogger(__name__)


class RedisAdvDataSnapshotStore:
    """Реализация ``AdvDataSnapshotStore`` на Redis."""

    def __init__(
        self,
        *,
        redis_client: Redis | None = None,
        ttl_sec: int | None = None,
        no_op: bool = True,
    ) -> None:
        """Args:
            redis_client: asyncio Redis; по умолчанию из ``RedisCalculatedKeywordsCacheManager``.
            ttl_sec: EX для ключей; по умолчанию ``get_snapshot_config().snapshot_ttl_sec``.
            no_op: stub path — не писать в Redis.
        """
        self._no_op = no_op
        self._ttl_sec = (
            ttl_sec if ttl_sec is not None else get_snapshot_config().snapshot_ttl_sec
        )
        if redis_client is not None:
            self._client = redis_client
        else:
            from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
                RedisCalculatedKeywordsCacheManager,
            )

            self._client = RedisCalculatedKeywordsCacheManager().client

    @property
    def is_no_op(self) -> bool:
        """Stub path — без записи/чтения Redis."""
        return self._no_op

    async def save(self, batch: ShopAdvSnapshotBatchDTO) -> None:
        """Сохраняет batch + per-adv ключи.

        Side effects:
            Redis SET с TTL (только при ``no_op=False``).
            Удаляет per-adv ключи РК, которые были в предыдущем batch, но отсутствуют
            в новом (в т.ч. пустой batch после сбоя PG или отсутствия active ads).
        """
        if self._no_op:
            logger.debug(
                "RedisAdvDataSnapshotStore.save (no-op): shop_id=%s snapshots=%d",
                batch.shop_id,
                len(batch.snapshots),
            )
            return
        new_adv_ids = {snap.adv_id for snap in batch.snapshots}
        stale_adv_ids: set[int] = set()
        if batch.snapshots:
            previous = await self.load_shop_latest(batch.shop_id)
            if previous is not None:
                stale_adv_ids = {snap.adv_id for snap in previous.snapshots} - new_adv_ids

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
        if not batch.snapshots:
            orphan_keys = await self._list_shop_per_adv_snapshot_keys(batch.shop_id)
            for key in orphan_keys:
                await self._client.delete(key)
            if orphan_keys:
                logger.debug(
                    "RedisAdvDataSnapshotStore.save removed orphan per-adv keys "
                    "(empty batch): shop_id=%s count=%d",
                    batch.shop_id,
                    len(orphan_keys),
                )
        else:
            for adv_id in stale_adv_ids:
                await self._client.delete(adv_snapshot_key(batch.shop_id, adv_id))
            if stale_adv_ids:
                logger.debug(
                    "RedisAdvDataSnapshotStore.save removed stale per-adv keys: "
                    "shop_id=%s adv_ids=%s",
                    batch.shop_id,
                    sorted(stale_adv_ids),
                )
        logger.debug(
            "RedisAdvDataSnapshotStore.save shop_id=%s snapshots=%d",
            batch.shop_id,
            len(batch.snapshots),
        )

    async def _list_shop_per_adv_snapshot_keys(self, shop_id: str) -> list[str]:
        """SCAN per-adv ключей магазина (восстановление после пустого latest без очистки)."""
        pattern = shop_per_adv_snapshot_pattern(shop_id)
        keys: list[str] = []
        cursor: int = 0
        while True:
            cursor, batch_keys = await self._client.scan(
                cursor=cursor,
                match=pattern,
                count=200,
            )
            for raw in batch_keys:
                keys.append(raw.decode() if isinstance(raw, bytes) else raw)
            if cursor == 0:
                break
        return keys

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
        except (TypeError, ValueError, ValidationError) as exc:
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
        except (TypeError, ValueError, ValidationError) as exc:
            logger.warning(
                "RedisAdvDataSnapshotStore.load_adv_snapshot invalid: shop=%s adv=%s %s",
                shop_id,
                adv_id,
                exc,
            )
            return None
