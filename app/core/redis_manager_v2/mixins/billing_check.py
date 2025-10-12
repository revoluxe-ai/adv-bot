"""Mixin for billing check operations in Redis."""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.redis_manager_v2.base_protocol import BaseRedisManagerProtocol


class BillingCheckMixin:
    prefix = "billing:processed"
    default_ttl = 93600  # 1 день ровно

    def _get_key(self: 'BaseRedisManagerProtocol', wb_cabinet_id: int, day: datetime) -> str:
        """Generate a Redis key for billing processing check.
        Сделано универсальным (*args, **kwargs), чтобы соответствовать протоколу BaseRedisManagerProtocol
        и не ломать структурную совместимость (устранение mypy: Invalid self argument ...).
        Ожидаемые параметры: (wb_cabinet_id: int, day: datetime) позиционно или именованно.
        """
        return f"{self.prefix}:{wb_cabinet_id}:{day.strftime('%Y-%m-%d')}"

    async def set_billing_process_for_day(self: 'BaseRedisManagerProtocol', wb_cabinet_id: int, day: datetime,
                                          ttl: int | None = None) -> None:
        """Set a flag in Redis indicating that billing has been processed for the given shop and day.
        Если TTL не задан и не определён в менеджере – ключ будет без истечения.
        """
        key = self._get_key(wb_cabinet_id, day)
        effective_ttl = self._resolve_ttl(ttl)
        await self._client.set(key, "1", ex=effective_ttl)

    async def get_billing_process_for_day(self: "BaseRedisManager", wb_cabinet_id: int, day: datetime) -> bool:
        """Check if billing has been processed for the given shop and day."""
        key = self._get_key(wb_cabinet_id, day)
        result = await self._client.get(key)
        return bool(result) if result else False
