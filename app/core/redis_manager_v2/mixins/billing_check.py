"""Mixin for billing check operations in Redis."""

from datetime import datetime
from typing import TypeVar, Generic

T = TypeVar("T", bound="BaseRedisManager")


class BillingCheckMixin(Generic[T]):
    """Mixin for billing check operations in Redis."""

    @staticmethod
    def _get_key(wb_cabinet_id: int, day: datetime) -> str:
        """Generate a Redis key for billing processing check."""
        return f"billing_processed:{wb_cabinet_id}:{day.strftime('%Y-%m-%d')}"

    async def set_billing_process_for_day(self: T, wb_cabinet_id: int, day: datetime) -> None:
        """Set a flag in Redis indicating that billing has been processed for the given shop and day."""
        key = self._get_key(wb_cabinet_id, day)
        await self.client.set(key, "1", ex=86400 * 2)

    async def get_billing_process_for_day(self: T, wb_cabinet_id: int, day: datetime) -> bool:
        """Check if billing has been processed for the given shop and day."""
        key = self._get_key(wb_cabinet_id, day)
        result = await self.client.get(key)
        return bool(result) if result else False
