"""Redis manager that stores the datetime of the last successful auto-budget top-up."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.core.redis_manager_v2.redis_client import RedisClient

_PREFIX = "auto-budget-last-success"
_TTL = int(timedelta(days=30).total_seconds())


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class RedisAutoBudgetLastSuccessManager:
    """Stores and retrieves last successful top-up time for an adv_setting."""

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    @staticmethod
    def _key(adv_setting_id: int) -> str:
        return f"{_PREFIX}:{adv_setting_id}"

    async def set(self, adv_setting_id: int) -> None:
        """Store the timestamp of a successful top-up for the given campaign."""
        key = self._key(adv_setting_id)
        payload = {"at": _now_utc().isoformat()}
        await self._redis_client.set(key, json.dumps(payload), ex=_TTL)

    async def get(self, adv_setting_id: int) -> dict[str, str] | None:
        """Load the last successful top-up time. Returns None if missing or invalid."""
        key = self._key(adv_setting_id)
        raw = await self._redis_client.get(key)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
            at = data.get("at", "")
            return {"at": at} if at else None
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
