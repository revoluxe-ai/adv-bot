import datetime

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager


class RedisClusterBidsTimestampManager(BaseRedisManager):
    prefix = "last_cluster_bids_update_timestamp"

    def _get_key(self) -> str:
        return self.prefix

    async def get(self) -> datetime.datetime | None:
        key = self._get_key()
        value = await self._client.get(key)
        if value is None:
            return None
        value_dt = datetime.datetime.fromisoformat(value)
        return value_dt

    async def set(self, timestamp: datetime.datetime) -> None:
        key: str = self._get_key()
        value_str = timestamp.astimezone(datetime.timezone.utc).isoformat()
        _ = await self._client.set(key, value_str)
        return None










