import datetime

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.modules.cluster_bids_redis.redis_cluster_bids_timestamp_manager import (
    _redis_adv_id_for_cluster_bids_timestamp,
)

from .adv_protocol import AdvProtocol


class RedisClusterBidsTimestampManager(BaseRedisManager):
    prefix = "last_cluster_bids_update_timestamp"

    def _get_key(self, adv: AdvProtocol) -> str:
        return f"{self.prefix}:{_redis_adv_id_for_cluster_bids_timestamp(adv)}"

    async def get(self, adv: AdvProtocol) -> datetime.datetime | None:
        key = self._get_key(adv)
        value = await self._client.get(key)
        if value is None:
            return None
        value_dt = datetime.datetime.fromisoformat(value)
        return value_dt

    async def set(self, adv: AdvProtocol) -> None:
        key: str = self._get_key(adv)
        value_str = datetime.datetime.now().isoformat()
        _ = await self._client.set(key, value_str)
        return None










