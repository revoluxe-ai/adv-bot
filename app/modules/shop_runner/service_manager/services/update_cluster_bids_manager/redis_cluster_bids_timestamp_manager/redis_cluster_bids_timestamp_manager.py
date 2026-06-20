import datetime

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager

from .adv_protocol import AdvProtocol

class RedisClusterBidsTimestampManager(BaseRedisManager):
    prefix = "last_cluster_bids_update_timestamp"

    def _get_key(self, search_adv_id: int) -> str:
        return f"{self.prefix}:{search_adv_id}"

    async def get(self, adv: AdvProtocol) -> datetime.datetime | None:
        search_adv_id = adv.search_adv_id
        if search_adv_id is None:
            return None
        key = self._get_key(search_adv_id)
        value = await self._client.get(key)
        if value is None:
            return None
        value_dt = datetime.datetime.fromisoformat(value)
        return value_dt

    async def set(self, adv: AdvProtocol) -> None:
        search_adv_id = adv.search_adv_id
        if search_adv_id is None:
            raise ValueError("adv.search_adv_id is None")
        key: str = self._get_key(search_adv_id)
        value_str = datetime.datetime.now().isoformat()
        _ = await self._client.set(key, value_str)
        return None










