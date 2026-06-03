"""Redis-снимок отчёта последнего V3-тика для UI бота."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3PhaseStats,
    V3TickReportSnapshot,
)

_TTL_SEC = int(timedelta(days=7).total_seconds())


class V3TickReportRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="V3TickReport",
):
    """Ключ ``V3TickReport:{adv_id}`` — отчёт стадий последнего V3-тика."""

    async def set(self, snapshot: V3TickReportSnapshot) -> None:
        """Сохранить отчёт с TTL 7 суток."""
        await self.client.set(self._key, snapshot.model_dump_json(), ex=_TTL_SEC)

    async def get(self) -> V3TickReportSnapshot | None:
        """Загрузить отчёт; ``None`` если ключа нет или JSON битый."""
        raw = await self.client.get(self._key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            data: dict[str, Any] = json.loads(raw)
            tick_val = data.get("tick_at")
            if tick_val:
                dt = datetime.fromisoformat(str(tick_val).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data["tick_at"] = dt
            phases_raw = data.get("phases")
            if isinstance(phases_raw, list):
                data["phases"] = [
                    V3PhaseStats.model_validate(p) if isinstance(p, dict) else p
                    for p in phases_raw
                ]
            return V3TickReportSnapshot.model_validate(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None


async def persist_v3_tick_report(
    adv: AdvSetting,
    snapshot: V3TickReportSnapshot,
) -> None:
    """Записать отчёт тика в Redis."""
    await V3TickReportRedisCache(adv).set(snapshot)
