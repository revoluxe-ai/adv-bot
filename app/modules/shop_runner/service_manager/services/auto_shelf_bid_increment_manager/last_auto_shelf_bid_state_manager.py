"""Кэш и persist последнего снимка: Redis + fallback ClickHouse prev."""

from __future__ import annotations

from datetime import timedelta

from app.core.redis_manager_v2.redis_client import RedisClient

from .auto_shelf_bid_repository import AutoShelfBidRepository
from .clickhouse_auto_shelf_bid_writer import ClickHouseAutoShelfBidWriter
from .dto import AutoShelfBidSnapshot


class LastAutoShelfBidStateManager:
    """Читает prev из Redis, при промахе — из CH; persist пишет Redis и CH."""

    _TTL = int(timedelta(hours=24).total_seconds())

    def __init__(
        self,
        redis_client: RedisClient,
        repository: AutoShelfBidRepository,
        writer: ClickHouseAutoShelfBidWriter,
    ) -> None:
        self._redis_client = redis_client
        self._repository = repository
        self._writer = writer

    @staticmethod
    def _redis_key(nmid: int) -> str:
        """Ключ last:auto_shelf_bid:{nmid}."""
        return f"last:auto_shelf_bid:{nmid}"

    @staticmethod
    def _resync_key(nmid: int) -> str:
        """Ключ маркера resync после negative recommendations."""
        return f"resync:auto_shelf_bid:{nmid}"

    async def get(self, nmid: int) -> tuple[AutoShelfBidSnapshot | None, str]:
        """Вернуть (snapshot, source): redis | clickhouse | none."""
        key = self._redis_key(nmid)
        raw = await self._redis_client.get(key)
        if raw:
            snapshot = AutoShelfBidSnapshot.from_redis(raw)
            if snapshot:
                return snapshot, "redis"

        snapshot = await self._repository.fetch_prev_auto_shelf_bid(nmid)
        if snapshot:
            _ = await self._redis_client.set(key, snapshot.to_redis(), ex=self._TTL)
            return snapshot, "clickhouse"
        return None, "none"

    async def persist(self, snapshot: AutoShelfBidSnapshot) -> None:
        """Обновить Redis-кэш и записать prev в ClickHouse."""
        key = self._redis_key(snapshot.nmid)
        _ = await self._redis_client.set(key, snapshot.to_redis(), ex=self._TTL)
        await self._writer.insert_prev(snapshot)

    async def mark_resync_required(self, nmid: int) -> None:
        """Выставить флаг обязательного resync на первом валидном тике."""
        key = self._resync_key(nmid)
        _ = await self._redis_client.set(key, "1", ex=self._TTL)

    async def is_resync_required(self, nmid: int) -> bool:
        """Проверить, нужен ли принудительный resync после negative ветки."""
        key = self._resync_key(nmid)
        return bool(await self._redis_client.get(key))

    async def clear_resync_required(self, nmid: int) -> None:
        """Снять флаг resync после успешного persist валидного snapshot."""
        key = self._resync_key(nmid)
        _ = await self._redis_client.delete(key)
