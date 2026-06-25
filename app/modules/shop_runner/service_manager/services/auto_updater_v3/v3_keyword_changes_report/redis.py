"""Redis-кеш полного audit изменений ключей V3."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangesSnapshot,
)

_TTL_SEC = int(timedelta(days=7).total_seconds())


class V3KeywordChangesRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="V3KeywordChanges",
):
    """Ключ ``V3KeywordChanges:{adv_id}`` — полный audit изменений ключей."""

    async def set(self, snapshot: V3KeywordChangesSnapshot) -> None:
        """Сохранить audit с TTL 7 суток."""
        await self.client.set(self._key, snapshot.model_dump_json(), ex=_TTL_SEC)

    async def get(self) -> V3KeywordChangesSnapshot | None:
        """Загрузить audit; ``None`` если ключа нет или JSON битый."""
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
            return V3KeywordChangesSnapshot.model_validate(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None


async def persist_v3_keyword_changes(
    adv: AdvSetting,
    snapshot: V3KeywordChangesSnapshot,
) -> None:
    """Записать audit изменений ключей в Redis."""
    await V3KeywordChangesRedisCache(adv).set(snapshot)
