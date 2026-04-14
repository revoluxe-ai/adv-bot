"""Redis cache for StatsFreshnessState per adv_id (filled by refresh_stats_freshness_cache)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessState,
)

EntryKind = Literal["hit", "miss", "invalid"]


class RedisStatsFreshnessStateCacheManager:
    """Caches automation freshness classification per WB adv_id for a shop."""

    _PREFIX = "stats_freshness_state"
    _TTL_SEC = 6 * 60 * 60  # 6 hours — aligned with emergency stale window

    def __init__(self, redis_client: RedisClient) -> None:
        self._client = redis_client

    @classmethod
    def key(cls, shop_id: str, adv_id: int) -> str:
        return f"{cls._PREFIX}:shop:{shop_id}:adv:{adv_id}"

    @staticmethod
    def _to_json(state: StatsFreshnessState) -> str:
        payload: dict[str, Any] = {
            "is_fresh": state.is_fresh,
            "is_stale_over_6h": state.is_stale_over_6h,
            "reason": state.reason,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _from_json(raw: str | bytes | None) -> StatsFreshnessState | None:
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        try:
            is_fresh = bool(data["is_fresh"])
            is_stale_over_6h = bool(data["is_stale_over_6h"])
            reason = data.get("reason")
            if reason is not None and not isinstance(reason, str):
                return None
            return StatsFreshnessState(
                is_fresh=is_fresh,
                is_stale_over_6h=is_stale_over_6h,
                reason=reason,
            )
        except (KeyError, TypeError, ValueError):
            return None

    async def mget_entries(
        self, shop_id: str, adv_ids: list[int]
    ) -> list[tuple[int, StatsFreshnessState | None, EntryKind]]:
        """Batch-read states; classify each key as hit / miss / invalid payload."""
        if not adv_ids:
            return []
        keys = [self.key(shop_id, adv_id) for adv_id in adv_ids]
        raws = await self._client.mget(keys)
        result: list[tuple[int, StatsFreshnessState | None, EntryKind]] = []
        for adv_id, raw in zip(adv_ids, raws, strict=True):
            if raw is None:
                result.append((adv_id, None, "miss"))
                continue
            state = self._from_json(raw)
            if state is None:
                result.append((adv_id, None, "invalid"))
            else:
                result.append((adv_id, state, "hit"))
        return result

    async def mset_states(
        self, shop_id: str, entries: list[tuple[int, StatsFreshnessState]]
    ) -> None:
        if not entries:
            return
        async with self._client.write_pipeline() as pipeline:
            for adv_id, state in entries:
                pipeline.set(
                    self.key(shop_id, adv_id),
                    self._to_json(state),
                    ex=self._TTL_SEC,
                )
            await pipeline.execute()
