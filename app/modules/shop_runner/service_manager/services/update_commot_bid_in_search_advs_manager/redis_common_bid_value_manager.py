from __future__ import annotations

from typing import Sequence

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager


class RedisCommonBidValueManager(BaseRedisManager):
    prefix = "last_common_bid_value"
    default_ttl = 60 * 60 * 24  # keep values for 24 hours

    def _get_key(self, adv_id: int, nmid: int) -> str:
        return f"{self.prefix}:{adv_id}:{nmid}"

    async def set_bids(self, adv_id: int, bids: dict[int, int]) -> None:
        if not bids:
            return None
        ttl = self._resolve_ttl()
        async with self._client.write_pipeline() as pipeline:  # type: ignore[reportUnknownMemberType]
            for nmid, bid in bids.items():
                key = self._get_key(adv_id, nmid)
                if ttl is not None:
                    pipeline.set(key, bid, ex=ttl)
                else:
                    pipeline.set(key, bid)
            await pipeline.execute()  # type: ignore[reportUnknownMemberType]
        return None

    async def get_bids(self, adv_id: int, nmids: Sequence[int]) -> dict[int, int]:
        if not nmids:
            return {}
        async with self._client.read_pipeline() as pipeline:
            for nmid in nmids:
                key = self._get_key(adv_id, nmid)
                pipeline.get(key)
            raw_results: list[str | None] = await pipeline.execute()
        bids: dict[int, int] = {}
        for nmid, raw in zip(nmids, raw_results):
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw_value = raw.decode()
            else:
                raw_value = raw
            try:
                bids[nmid] = int(raw_value)
            except (TypeError, ValueError):
                continue
        return bids


__all__ = ["RedisCommonBidValueManager"]
