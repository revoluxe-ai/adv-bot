"""Redis storage for cluster bids (adv_id, nmid, cluster -> bid value)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from typing import Sequence
from typing import cast

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager


@dataclass(frozen=True)
class ClusterBidKey:
    adv_id: int
    nmid: int
    cluster: str


@dataclass(frozen=True)
class ClusterBidEntry:
    """Single bid to store: adv_id, nmid, cluster, new_bid."""

    adv_id: int
    nmid: int
    cluster: str
    new_bid: int
    step: int | None = None
    direct: str | None = None


@dataclass(frozen=True)
class ClusterBidState:
    step: int | None
    direct: str | None


class RedisClusterBidsManager(BaseRedisManager):
    prefix = "cluster-bid"
    default_ttl = 60 * 60 * 12  # 12 часов

    def _get_key(self, adv_id: int, nmid: int, cluster: str) -> str:
        return f"{self.prefix}:{adv_id}:{nmid}:{cluster}"

    @staticmethod
    def _decode_raw(raw: str | bytes | None) -> tuple[int | None, ClusterBidState]:
        def _parse_int(value: object) -> int | None:
            if value is None or isinstance(value, bool):
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, (float, str)):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
            return None

        empty_state = ClusterBidState(step=None, direct=None)
        if raw is None:
            return None, empty_state
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            try:
                return int(raw), empty_state
            except (TypeError, ValueError):
                return None, empty_state
        if not isinstance(payload, dict):
            return _parse_int(payload), empty_state

        payload_obj = cast(dict[str, object], payload)
        bid = _parse_int(payload_obj.get("new_bid"))
        step = _parse_int(payload_obj.get("step"))
        direct_raw = payload_obj.get("direct")
        direct = direct_raw if isinstance(direct_raw, str) else None
        return bid, ClusterBidState(step=step, direct=direct)

    async def remember_bids(self, bids: Sequence[ClusterBidEntry]) -> None:
        if not bids:
            return
        ttl = self._resolve_ttl()
        async with self._client.write_pipeline() as pipeline:  # type: ignore[reportUnknownMemberType]
            for bid in bids:
                key = self._get_key(bid.adv_id, bid.nmid, bid.cluster)
                payload: dict[str, Any] = {
                    "new_bid": bid.new_bid,
                    "step": bid.step,
                    "direct": bid.direct,
                }
                payload_str = json.dumps(payload, ensure_ascii=False)
                if ttl is not None:
                    pipeline.set(key, payload_str, ex=ttl)
                else:
                    pipeline.set(key, payload_str)
            await pipeline.execute()  # type: ignore[reportUnknownMemberType]

    async def get_bids(
        self, keys: Sequence[ClusterBidKey]
    ) -> dict[ClusterBidKey, int]:
        if not keys:
            return {}
        async with self._client.read_pipeline() as pipeline:  # pyright: ignore
            for key in keys:
                redis_key = self._get_key(key.adv_id, key.nmid, key.cluster)
                pipeline.get(redis_key)
            raw_results: list[str | None] = await pipeline.execute()  # pyright: ignore
        bids: dict[ClusterBidKey, int] = {}
        for key, raw in zip(keys, raw_results):  # pyright: ignore
            bid, _ = self._decode_raw(raw)
            if bid is not None:
                bids[key] = bid
        return bids

    async def get_bid_states(
        self, keys: Sequence[ClusterBidKey]
    ) -> dict[ClusterBidKey, ClusterBidState]:
        if not keys:
            return {}
        async with self._client.read_pipeline() as pipeline:  # pyright: ignore
            for key in keys:
                redis_key = self._get_key(key.adv_id, key.nmid, key.cluster)
                pipeline.get(redis_key)
            raw_results: list[str | None] = await pipeline.execute()  # pyright: ignore
        states: dict[ClusterBidKey, ClusterBidState] = {}
        for key, raw in zip(keys, raw_results):  # pyright: ignore
            _, state = self._decode_raw(raw)
            if state.step is None and state.direct is None:
                continue
            states[key] = state
        return states


__all__ = [
    "RedisClusterBidsManager",
    "ClusterBidKey",
    "ClusterBidEntry",
    "ClusterBidState",
]
