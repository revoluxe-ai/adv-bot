"""Redis cache for normquery cluster bids as returned by WB API (no step/direct state)."""

from __future__ import annotations

import json
from collections.abc import Sequence

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager

from app.modules.cluster_bids_redis.redis_cluster_bids_manager import ClusterBidKey


class RedisApiClusterBidsManager(BaseRedisManager):
    """Separate key namespace from RedisClusterBidsManager (bidder-applied state)."""

    prefix = "api-cluster-bid"
    default_ttl = 60 * 60 * 12  # 12 hours, aligned with RedisClusterBidsManager

    def _get_key(self, adv_id: int, nmid: int, cluster: str) -> str:
        return f"{self.prefix}:{adv_id}:{nmid}:{cluster}"

    async def replace_from_api(self, bids: list[NormqueryBidDTO]) -> None:
        if not bids:
            return
        ttl = self._resolve_ttl()
        async with self._client.write_pipeline() as pipeline:  # type: ignore[reportUnknownMemberType]
            for dto in bids:
                key = self._get_key(dto.advert_id, dto.nm_id, dto.norm_query)
                payload = json.dumps({"bid": dto.bid}, ensure_ascii=False)
                if ttl is not None:
                    pipeline.set(key, payload, ex=ttl)
                else:
                    pipeline.set(key, payload)
            await pipeline.execute()  # type: ignore[reportUnknownMemberType]

    async def get_bids(self, keys: Sequence[ClusterBidKey]) -> dict[ClusterBidKey, int]:
        if not keys:
            return {}
        async with self._client.read_pipeline() as pipeline:  # pyright: ignore
            for key in keys:
                redis_key = self._get_key(key.adv_id, key.nmid, key.cluster)
                pipeline.get(redis_key)
            raw_results: list[str | None] = await pipeline.execute()  # pyright: ignore
        result: dict[ClusterBidKey, int] = {}
        for key, raw in zip(keys, raw_results):  # pyright: ignore
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and "bid" in data:
                    result[key] = int(data["bid"])
                elif isinstance(data, int):
                    result[key] = data
                else:
                    continue
            except (TypeError, ValueError, json.JSONDecodeError):
                try:
                    result[key] = int(raw)
                except (TypeError, ValueError):
                    continue
        return result


__all__ = ["RedisApiClusterBidsManager"]
