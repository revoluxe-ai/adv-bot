from __future__ import annotations

from datetime import datetime

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager


class RedisCommonBidTimestampManager(BaseRedisManager):
    prefix = "last_common_bid_search_update_timestamp"

    def _get_key(self, search_adv_id: int) -> str:
        return f"{self.prefix}:{search_adv_id}"

    async def get(self, search_adv_id: int) -> datetime | None:
        key = self._get_key(search_adv_id)
        value = await self._client.get(key)
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    async def set(self, search_adv_id: int) -> None:
        key = self._get_key(search_adv_id)
        value_str = datetime.now().isoformat()
        ttl = self._resolve_ttl()
        if ttl is None:
            _ = await self._client.set(key, value_str)
        else:
            _ = await self._client.set(key, value_str, ex=ttl)
        return None
