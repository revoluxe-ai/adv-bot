"""Redis manager that stores the fact that auto-budget top-up failed (e.g. not enough balance)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from app.core.redis_manager_v2.redis_client import RedisClient

_PREFIX = "auto-budget-topup-failed"
_TTL = int(timedelta(days=7).total_seconds())

REASON_NOT_ENOUGH_BALANCE = "not_enough_balance"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class RedisAutoBudgetTopupFailedManager:
    """Stores and retrieves last top-up failure for an adv_setting (by adv_setting_id)."""

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    @staticmethod
    def _key(adv_setting_id: int) -> str:
        return f"{_PREFIX}:{adv_setting_id}"

    async def set(
        self,
        adv_setting_id: int,
        reason: str = REASON_NOT_ENOUGH_BALANCE,
    ) -> None:
        """Store the fact that top-up failed for the given campaign."""
        key = self._key(adv_setting_id)
        payload = {
            "failed_at": _now_utc().isoformat(),
            "reason": reason,
        }
        _ = await self._redis_client.set(key, json.dumps(payload), ex=_TTL)

    async def get(
        self,
        adv_setting_id: int,
    ) -> dict[str, str] | None:
        """Load the last stored failure. Returns None if missing or invalid."""
        key = self._key(adv_setting_id)
        raw = await self._redis_client.get(key)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
            data = cast(dict[str, Any], data)
            failed_at: str = str(data.get("failed_at", ""))
            reason: str = str(data.get("reason", REASON_NOT_ENOUGH_BALANCE))
            return {"failed_at": failed_at, "reason": reason}
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
