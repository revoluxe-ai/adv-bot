"""Redis-кеш полного trace решений V3 по operable keywords."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceSnapshot,
)

_TTL_SEC = int(timedelta(days=7).total_seconds())


class KeywordDecisionTraceRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="KeywordDecisionTrace",
):
    """Ключ ``KeywordDecisionTrace:{adv_id}`` — полный cascade operable keywords."""

    async def set(self, snapshot: KeywordDecisionTraceSnapshot) -> None:
        """Сохранить trace с TTL 7 суток."""
        await self.client.set(self._key, snapshot.model_dump_json(), ex=_TTL_SEC)

    async def get(self) -> KeywordDecisionTraceSnapshot | None:
        """Загрузить trace; ``None`` если ключа нет или JSON битый."""
        raw = await self.client.get(self._key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            data: dict[str, Any] = json.loads(raw)
            for field in (
                "tick_started_at",
                "processing_started_at",
                "tick_finished_at",
                "tick_at",
            ):
                tick_val = data.get(field)
                if tick_val:
                    dt = datetime.fromisoformat(str(tick_val).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    data[field] = dt
            for entry in data.get("entries", []):
                psa = entry.get("processing_started_at")
                if psa:
                    dt = datetime.fromisoformat(str(psa).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    entry["processing_started_at"] = dt
                for step in entry.get("steps", []):
                    pa = step.get("processed_at")
                    if pa:
                        dt = datetime.fromisoformat(str(pa).replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        step["processed_at"] = dt
            return KeywordDecisionTraceSnapshot.model_validate(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None


async def persist_keyword_decision_trace(
    adv: AdvSetting,
    snapshot: KeywordDecisionTraceSnapshot,
) -> None:
    """Записать trace решений ключей в Redis."""
    await KeywordDecisionTraceRedisCache(adv).set(snapshot)
