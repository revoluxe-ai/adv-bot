"""UTC-day latch per leg slot для anti-gaming fair leg-pause billing.

SoT: Redis billing-owned keys (design §Latch SoT). Forbidden: запись из
shop-runner / pause paths.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Protocol

_SLOT_WEIGHT = 0.5


class AdvPaymentLegSlot(StrEnum):
    """Слоты биллинга; совпадают с AdvPayment.type."""

    AUTO_LEG = "auto_leg"
    SEARCH_LEG = "search_leg"


class _LegLatchRedis(Protocol):
    async def get(self, key: str) -> Any: ...
    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        px: int | None = None,
        nx: bool | None = None,
    ) -> Any: ...


class LegLatchManager:
    """Max billable weight слота за UTC-день в Redis."""

    KEY_PREFIX = "billing:leg_latch"
    TTL_SECONDS = 48 * 3600

    def __init__(self, client: _LegLatchRedis) -> None:
        self._client = client

    @staticmethod
    def _format_weight(weight: float) -> str:
        return "0.5" if weight >= _SLOT_WEIGHT else "0"

    @staticmethod
    def _parse_weight(raw: str | bytes | None) -> float:
        if raw is None:
            return 0.0
        text = raw.decode() if isinstance(raw, bytes) else raw
        return 0.5 if text == "0.5" else 0.0

    def _key(self, anchor_adv_setting_id: int, leg_slot: AdvPaymentLegSlot, utc_date: date) -> str:
        return (
            f"{self.KEY_PREFIX}:{anchor_adv_setting_id}:"
            f"{leg_slot.value}:{utc_date.isoformat()}"
        )

    async def record_sample(
        self,
        anchor_adv_setting_id: int,
        leg_slot: AdvPaymentLegSlot,
        instant_weight: float,
        utc_date: date,
    ) -> float:
        """SET max(existing, instant_weight); возвращает итоговый latch."""
        key = self._key(anchor_adv_setting_id, leg_slot, utc_date)
        new_weight = _SLOT_WEIGHT if instant_weight >= _SLOT_WEIGHT else 0.0
        existing = await self.get_billable_weight(
            anchor_adv_setting_id, leg_slot, utc_date
        )
        merged = max(existing, new_weight)
        await self._client.set(
            key,
            self._format_weight(merged),
            ex=self.TTL_SECONDS,
        )
        return merged

    async def get_billable_weight(
        self,
        anchor_adv_setting_id: int,
        leg_slot: AdvPaymentLegSlot,
        utc_date: date,
    ) -> float:
        """Прочитать max billable weight слота за UTC-день."""
        key = self._key(anchor_adv_setting_id, leg_slot, utc_date)
        raw = await self._client.get(key)
        return self._parse_weight(raw)
