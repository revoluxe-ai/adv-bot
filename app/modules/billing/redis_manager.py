from datetime import datetime

from app.core.redis_manager_v2.base_protocol import BaseRedisManagerProtocol
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.core.redis_manager_v2.mixins.billing_check import BillingCheckMixin
from app.modules.billing.leg_latch import LegLatchManager


class RedisManager(BillingCheckMixin, BaseRedisManager, BaseRedisManagerProtocol):
    """Менеджер для проверки биллинга в Redis с поддержкой TTL и префикса."""

    last_charge_prefix = "billing:last_charge_at"

    def leg_latch(self) -> LegLatchManager:
        """Latch per leg / UTC-день (fair leg-pause billing)."""
        return LegLatchManager(self._client)

    def _get_last_charge_key(self, shop_id: str) -> str:
        return f"{self.last_charge_prefix}:{shop_id}"

    async def set_last_charge_at(
        self, shop_id: str, charged_at: datetime, ttl: int | None = None
    ) -> None:
        key = self._get_last_charge_key(shop_id)
        effective_ttl = self._resolve_ttl(ttl)
        _ = await self._client.set(key, charged_at.isoformat(), ex=effective_ttl)

    async def get_last_charge_at(self, shop_id: str) -> datetime | None:
        key = self._get_last_charge_key(shop_id)
        value = await self._client.get(key)
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
