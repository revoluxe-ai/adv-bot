from __future__ import annotations

from datetime import timedelta
from typing import Tuple
from uuid import UUID

from app.core.redis_manager_v2.redis_client import RedisClient

from .dto.fact_stat_snapshot import FactStatSnapshot
from .fact_stat_repository import FactStatRepository


class LastStateManager:
    _TTL = int(timedelta(hours=24).total_seconds())

    def __init__(
        self,
        redis_client: RedisClient,
        repository: FactStatRepository,
    ) -> None:
        self._redis_client = redis_client
        self._repository = repository

    @staticmethod
    def _redis_key(shop_id: str, complex_adv_id: int) -> str:
        return f"last:fact:{shop_id}:{complex_adv_id}"

    async def get(
        self, shop_id: str, complex_adv_id: int
    ) -> Tuple[FactStatSnapshot | None, str]:
        try:
            uuid_str = UUID(shop_id)
        except ValueError:
            return None, "none"
        key = self._redis_key(str(uuid_str), complex_adv_id)
        raw = await self._redis_client.get(key)
        if raw:
            snapshot = FactStatSnapshot.from_redis(raw)
            if snapshot:
                return snapshot, "redis"

        snapshot = await self._repository.fetch_prev_fact_state(
            uuid_str, complex_adv_id
        )
        if snapshot:
            _ = await self._redis_client.set(
                key, snapshot.to_redis(), ex=self._TTL
            )
            return snapshot, "clickhouse"
        return None, "none"

    async def persist(self, snapshot: FactStatSnapshot) -> None:
        key = self._redis_key(str(snapshot.shop_id), snapshot.complex_adv_id)
        _ = await self._redis_client.set(
            key, snapshot.to_redis(), ex=self._TTL
        )
        await self._repository.upsert_prev_fact_state(snapshot)
