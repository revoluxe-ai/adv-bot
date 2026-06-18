from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    NewBid,
)


@dataclass(frozen=True)
class ClusterBidKey:
    adv_id: int
    nmid: int
    cluster: str


class RedisClusterBidsManager(BaseRedisManager):
    prefix = "cluster-bid"
    default_ttl = 60 * 60 * 12  # 12 часов

    def _get_key(self, adv_id: int, nmid: int, cluster: str) -> str:
        return f"{self.prefix}:{adv_id}:{nmid}:{cluster}"
    # TODO: решить вопрос с Pipeline, чтобы не было проблем с типизацией
    async def remember_bids(self, bids: Sequence[NewBid]) -> None:
        if not bids:
            return
        ttl = self._resolve_ttl()
        async with self._client.write_pipeline() as pipeline:  # type: ignore[reportUnknownMemberType]
            for bid in bids:
                key = self._get_key(bid.search_adv_id, bid.nmid, bid.cluster)
                if ttl is not None:
                    pipeline.set(key, bid.new_bid, ex=ttl)
                else:
                    pipeline.set(key, bid.new_bid)
            await pipeline.execute()  # type: ignore[reportUnknownMemberType]

    async def get_bids(
        self, keys: Sequence[ClusterBidKey]
    ) -> dict[ClusterBidKey, int]:
        if not keys:
            return {}
        async with self._client.read_pipeline() as pipeline: # pyright: ignore
            for key in keys:
                redis_key = self._get_key(key.adv_id, key.nmid, key.cluster)
                pipeline.get(redis_key)
            raw_results: list[str | None] = await pipeline.execute() # pyright: ignore
        bids: dict[ClusterBidKey, int] = {}
        for key, raw in zip(keys, raw_results): # pyright: ignore
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                bids[key] = int(raw)
            except (TypeError, ValueError):
                continue
        return bids

__all__ = ["RedisClusterBidsManager", "ClusterBidKey"]

