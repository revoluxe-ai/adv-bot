"""
Порт authoritative current/effective unit price для product control.

Slice A: только контракт; production adapter — Slice D после закрытия price SoT.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.modules.product_control.domain.models import ProductRef


@dataclass(frozen=True, slots=True)
class EffectiveProductPrice:
    """Наблюдённая effective price для control (не historical GMV/order)."""

    price_rub: Decimal
    observed_at: datetime
    source: str


@dataclass(frozen=True, slots=True)
class ProductPriceUnavailable:
    """Цена недоступна или не прошла политику staleness."""

    reason: str


ProductPriceReadResult = EffectiveProductPrice | ProductPriceUnavailable


class ProductPricingReader(Protocol):
    """
    Единственный authority port для ``effective_product_price`` в ProductCpoResolver.

    ``wb_common_stat`` и AdvSetting.target_price_for_order запрещены как substitute.
    """

    async def get_effective_price(
        self,
        product: ProductRef,
    ) -> ProductPriceReadResult:
        """Вернуть effective unit price или ProductPriceUnavailable."""
        ...
