"""Redis-снимок последнего применённого V3-действия для UI бота (блок «Обновл:»)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)

_TTL_SEC = int(timedelta(days=7).total_seconds())
_KEYWORD_TEXT_MAX_LEN = 40


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class LastV3UpdaterActionSnapshot(BaseModel):
    """Последнее успешно применённое V3-действие по кампании."""

    updated_at: datetime
    action: V3ActionType
    keyword_text: str = ""
    keyword_setting_id: int | None = None
    from_mode: str
    to_mode: str
    reason: str = ""
    batch_extra_count: int = 0
    cycle_aggregate: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}

    def to_redis(self) -> str:
        """Сериализация в JSON для Redis (``updated_at`` — UTC ISO)."""
        payload: dict[str, Any] = {
            "updated_at": self.updated_at.isoformat(),
            "action": self.action.value,
            "keyword_text": self.keyword_text,
            "keyword_setting_id": self.keyword_setting_id,
            "from_mode": self.from_mode,
            "to_mode": self.to_mode,
            "reason": self.reason,
            "batch_extra_count": self.batch_extra_count,
            "cycle_aggregate": self.cycle_aggregate,
        }
        return json.dumps(payload, ensure_ascii=False)

    @classmethod
    def from_redis(cls, raw: str) -> LastV3UpdaterActionSnapshot | None:
        """Десериализация из Redis; ``None`` при невалидных данных."""
        try:
            data = json.loads(raw)
            updated_val = data.get("updated_at")
            action_val = data.get("action")
            if not updated_val or not action_val:
                return None
            updated_at = datetime.fromisoformat(
                str(updated_val).replace("Z", "+00:00")
            )
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            return cls(
                updated_at=updated_at,
                action=V3ActionType(action_val),
                keyword_text=str(data.get("keyword_text") or ""),
                keyword_setting_id=data.get("keyword_setting_id"),
                from_mode=str(data.get("from_mode") or ""),
                to_mode=str(data.get("to_mode") or ""),
                reason=str(data.get("reason") or ""),
                batch_extra_count=int(data.get("batch_extra_count") or 0),
                cycle_aggregate=(
                    data.get("cycle_aggregate")
                    if isinstance(data.get("cycle_aggregate"), dict)
                    else None
                ),
            )
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            return None


def truncate_keyword_text(text: str, *, max_len: int = _KEYWORD_TEXT_MAX_LEN) -> str:
    """Обрезка текста ключа для строки Telegram-меню."""
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def build_snapshot_from_applied(
    *,
    action: V3ActionType,
    keyword_text: str,
    keyword_setting_id: int | None,
    from_mode: KeywordStrategyMode,
    to_mode: KeywordStrategyMode,
    reason: str,
    batch_extra_count: int,
    cycle_aggregate: dict[str, Any] | None = None,
    updated_at: datetime | None = None,
) -> LastV3UpdaterActionSnapshot:
    """Собрать snapshot для записи в Redis после успешного apply."""
    return LastV3UpdaterActionSnapshot(
        updated_at=updated_at or _now_utc(),
        action=action,
        keyword_text=truncate_keyword_text(keyword_text),
        keyword_setting_id=keyword_setting_id,
        from_mode=from_mode.name,
        to_mode=to_mode.name,
        reason=reason[:30] if reason else "",
        batch_extra_count=max(0, batch_extra_count),
        cycle_aggregate=cycle_aggregate,
    )


class LastV3UpdaterActionRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="LastV3UpdaterAction",
):
    """Ключ ``LastV3UpdaterAction:{adv_id}`` — последнее V3-действие для UI."""

    async def set(self, snapshot: LastV3UpdaterActionSnapshot) -> None:
        """Сохранить снимок с TTL 7 суток."""
        await self.client.set(self._key, snapshot.to_redis(), ex=_TTL_SEC)

    async def get(self) -> LastV3UpdaterActionSnapshot | None:
        """Загрузить снимок; ``None`` если ключа нет или JSON битый."""
        raw = await self.client.get(self._key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return LastV3UpdaterActionSnapshot.from_redis(raw)
