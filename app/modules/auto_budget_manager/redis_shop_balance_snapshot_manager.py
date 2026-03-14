"""Redis manager that stores last balance snapshot per shop (balance, net, bonus)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from app.core.redis_manager_v2.redis_client import RedisClient

_PREFIX = "shop-balance-snapshot"
_TTL = int(timedelta(hours=48).total_seconds())


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class RedisShopBalanceSnapshotManager:
    """Stores and retrieves last balance snapshot for a shop (by shop_id)."""

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    @staticmethod
    def _key(shop_id: str | int) -> str:
        return f"{_PREFIX}:{shop_id}"

    async def set(
        self,
        shop_id: str | int,
        balance: int,
        net: int,
        bonus: int,
    ) -> None:
        """Store balance snapshot for the given shop."""
        key = self._key(shop_id)
        payload = {
            "balance": balance,
            "net": net,
            "bonus": bonus,
            "updated_at": _now_utc().isoformat(),
        }
        await self._redis_client.set(key, json.dumps(payload), ex=_TTL)

    async def get(
        self,
        shop_id: str | int,
    ) -> dict[str, int | str] | None:
        """Load the last stored balance snapshot. Returns None if missing or invalid."""
        key = self._key(shop_id)
        raw = await self._redis_client.get(key)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
            data = cast(dict[str, Any], data)
            balance_raw: Any = data.get("balance", 0)
            net_raw: Any = data.get("net", 0)
            bonus_raw: Any = data.get("bonus", 0)
            updated_at: str = str(data.get("updated_at", ""))
            return {
                "balance": int(balance_raw) if balance_raw is not None else 0,
                "net": int(net_raw) if net_raw is not None else 0,
                "bonus": int(bonus_raw) if bonus_raw is not None else 0,
                "updated_at": updated_at,
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
