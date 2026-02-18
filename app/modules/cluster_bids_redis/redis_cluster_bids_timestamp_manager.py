"""Redis storage for last cluster bids update timestamp per adv."""

from __future__ import annotations

import datetime
from typing import Protocol, runtime_checkable


from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager


@runtime_checkable
class AdvProtocol(Protocol):
    @property
    def adv_id(self) -> int: ...


class RedisClusterBidsTimestampManager(BaseRedisManager):
    prefix = "last_cluster_bids_update_timestamp"

    def _get_key(self, adv: AdvProtocol) -> str:
        return f"{self.prefix}:{adv.adv_id}"

    async def get(self, adv: AdvProtocol) -> datetime.datetime | None:
        key = self._get_key(adv)
        value = await self._client.get(key)
        if value is None:
            return None
        value_dt = datetime.datetime.fromisoformat(value)
        return value_dt

    async def set(self, adv: AdvProtocol) -> None:
        key = self._get_key(adv)
        value_str = datetime.datetime.now().isoformat()
        await self._client.set(key, value_str)
