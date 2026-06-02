"""Redis storage for last cluster bids update timestamp per adv."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
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
        """Записать timestamp последнего обновления cluster bids для одной РК."""
        await self.set_many([adv])

    async def set_many(self, advs: Sequence[AdvProtocol]) -> None:
        """Записать timestamp для нескольких РК одним Redis pipeline (batch SET).

        Args:
            advs: РК; при повторе ``adv_id`` ключ пишется один раз.
        """
        if not advs:
            return
        value_str = datetime.datetime.now().isoformat()
        ttl = self._resolve_ttl()
        seen_adv_ids: set[int] = set()
        async with self._client.write_pipeline() as pipeline:  # type: ignore[reportUnknownMemberType]
            for adv in advs:
                if adv.adv_id in seen_adv_ids:
                    continue
                seen_adv_ids.add(adv.adv_id)
                key = self._get_key(adv)
                if ttl is not None:
                    pipeline.set(key, value_str, ex=ttl)
                else:
                    pipeline.set(key, value_str)
            await pipeline.execute()  # type: ignore[reportUnknownMemberType]
