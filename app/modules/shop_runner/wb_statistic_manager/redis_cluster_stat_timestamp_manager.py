from __future__ import annotations

from datetime import datetime

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager


class RedisClusterStatTimestampManager(BaseRedisManager):
    prefix = "last_cluster_stat_update_timestamp"

    def _get_key(self, adv_id: int) -> str:
        return f"{self.prefix}:{adv_id}"

    async def get(self, adv_id: int) -> datetime | None:
        key = self._get_key(adv_id)
        value = await self._client.get(key)
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    async def set(self, adv_id: int) -> None:
        key = self._get_key(adv_id)
        value_str = datetime.now().isoformat()
        ttl = self._resolve_ttl()
        if ttl is None:
            _ = await self._client.set(key, value_str)
        else:
            _ = await self._client.set(key, value_str, ex=ttl)
        return None
