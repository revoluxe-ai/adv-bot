"""Redis: время последнего отключения ключа по правилу «выше цели при мин. ставке»."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.redis_manager_v2.base_protocol import BaseRedisManagerProtocol
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager

if TYPE_CHECKING:
    pass

# 25 ч — покрывает цикл 24 ч BAD + 1 ч перетест; автоочистка при сбоях
_TTL_SECONDS = 25 * 60 * 60


def normalize_cooldown_keyword_text(text: str) -> str:
    return text.strip().casefold()


class RedisAboveTargetMinBidCooldownManager(BaseRedisManager, BaseRedisManagerProtocol):
    """Ключ: kw_cooldown:above_target_min:{adv_id}:{normalized_text} → Unix timestamp (float str)."""

    prefix = "kw_cooldown:above_target_min"
    default_ttl = _TTL_SECONDS

    def _get_key(self, adv_id: int, normalized_text: str) -> str:
        return f"{self.prefix}:{adv_id}:{normalized_text}"

    async def get_many(self, adv_id: int, texts: list[str]) -> dict[str, datetime | None]:
        """По исходным text (как в БД) → last_disabled_at или None."""
        result: dict[str, datetime | None] = {}
        for text in texts:
            norm = normalize_cooldown_keyword_text(text)
            raw = await self._client.get(self._get_key(adv_id, norm))
            if not raw:
                result[text] = None
                continue
            try:
                ts = float(raw)
                result[text] = datetime.fromtimestamp(ts, tz=UTC)
            except (TypeError, ValueError):
                result[text] = None
        return result

    async def apply_updates(
        self, adv_id: int, updates: dict[str, datetime | None]
    ) -> None:
        """None в updates — удалить ключ; datetime — записать с TTL."""
        if not updates:
            return
        ttl = self._resolve_ttl()
        for text, at in updates.items():
            norm = normalize_cooldown_keyword_text(text)
            key = self._get_key(adv_id, norm)
            if at is None:
                await self._client.delete(key)
            else:
                ts = at.timestamp()
                await self._client.set(key, str(ts), ex=ttl)
