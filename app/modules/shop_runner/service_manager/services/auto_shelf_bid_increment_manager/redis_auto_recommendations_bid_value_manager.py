"""Redis-кэш текущих ставок полок Auto-кампаний по ключу auto_adv_id+nmid."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from redis.client import Pipeline

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager


@dataclass(frozen=True, slots=True)
class AutoRecommendationsBidCacheValue:
    """Кэш-значение текущей ставки полок и времени обновления."""

    bid_minor: int
    updated_at: datetime


class RedisAutoRecommendationsBidValueManager(BaseRedisManager):
    """Кэширует recommendations bid (копейки) из WB v2 adverts."""

    prefix = "last_auto_recommendations_bid_value"
    default_ttl = 60 * 60 * 24

    def _get_key(self, auto_adv_id: int, nmid: int) -> str:
        """Сформировать ключ Redis для auto_adv_id + nmid."""
        return f"{self.prefix}:{auto_adv_id}:{nmid}"

    @staticmethod
    def _serialize(value: AutoRecommendationsBidCacheValue) -> str:
        """Сериализовать значение в JSON."""
        return json.dumps(
            {"bid_minor": value.bid_minor, "updated_at": value.updated_at.isoformat()},
            ensure_ascii=False,
        )

    @staticmethod
    def _deserialize(raw_value: str | bytes | int | float | None) -> AutoRecommendationsBidCacheValue | None:
        """Десериализовать JSON; при некорректном payload вернуть None."""
        if raw_value is None:
            return None
        if isinstance(raw_value, bytes):
            text = raw_value.decode()
        elif isinstance(raw_value, (str, int, float)):
            text = str(raw_value)
        else:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        bid_raw = parsed.get("bid_minor")
        updated_at_raw = parsed.get("updated_at")
        if not isinstance(bid_raw, int):
            return None
        if not isinstance(updated_at_raw, str):
            return None
        try:
            updated_at = datetime.fromisoformat(updated_at_raw)
        except ValueError:
            return None
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        return AutoRecommendationsBidCacheValue(
            bid_minor=bid_raw,
            updated_at=updated_at,
        )

    async def set_bids(
        self,
        auto_adv_id: int,
        bids: dict[int, int],
        *,
        updated_at: datetime | None = None,
    ) -> None:
        """Сохранить набор ставок для одной auto-кампании."""
        if not bids:
            return None
        ts = updated_at or datetime.now(timezone.utc)
        ttl = self._resolve_ttl()
        pipeline: Pipeline
        async with self._client.write_pipeline() as pipeline:  # pyright: ignore[reportUnknownMemberType]
            for nmid, bid_minor in bids.items():
                if bid_minor <= 0:
                    continue
                key = self._get_key(auto_adv_id, nmid)
                payload = self._serialize(
                    AutoRecommendationsBidCacheValue(
                        bid_minor=int(bid_minor),
                        updated_at=ts,
                    )
                )
                if ttl is None:
                    pipeline.set(key, payload)
                else:
                    pipeline.set(key, payload, ex=ttl)
            await pipeline.execute()  # pyright: ignore[reportUnknownMemberType]
        return None

    async def get_bids(
        self,
        auto_adv_id: int,
        nmids: Sequence[int],
    ) -> dict[int, AutoRecommendationsBidCacheValue]:
        """Прочитать ставки по списку nmid для одной auto-кампании."""
        if not nmids:
            return {}
        async with self._client.read_pipeline() as pipeline:  # pyright: ignore[reportUnknownMemberType]
            for nmid in nmids:
                _ = pipeline.get(self._get_key(auto_adv_id, nmid))
            raw_values = await pipeline.execute()  # pyright: ignore[reportUnknownMemberType]
        result: dict[int, AutoRecommendationsBidCacheValue] = {}
        for nmid, raw in zip(nmids, raw_values):
            parsed = self._deserialize(raw)
            if parsed is None:
                continue
            result[int(nmid)] = parsed
        return result

    async def get_bid(
        self,
        auto_adv_id: int,
        nmid: int,
    ) -> AutoRecommendationsBidCacheValue | None:
        """Прочитать ставку для одного nmid."""
        key = self._get_key(auto_adv_id, nmid)
        raw = await self._client.get(key)
        return self._deserialize(raw)


__all__ = [
    "AutoRecommendationsBidCacheValue",
    "RedisAutoRecommendationsBidValueManager",
]
