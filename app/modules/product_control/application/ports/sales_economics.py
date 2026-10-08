"""
Порт исторической sales economics (аналитика), отделённый от pricing.

Данные wb_common_stat и производные revenue-per-order — только здесь.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.modules.product_control.domain.models import ProductRef


@dataclass(frozen=True, slots=True)
class ProductSalesEconomicsSnapshot:
    """Агрегаты продаж за период; не подставляются в ProductCpoResolver."""

    period_start: date
    period_end: date
    orders_count: int | None
    orders_sum_rub: Decimal | None


class ProductSalesEconomicsReader(Protocol):
    """Read-side контракт для capacity/analytics; не смешивать с ProductPricingReader."""

    async def get_sales_economics(
        self,
        product: ProductRef,
        period_start: date,
        period_end: date,
    ) -> ProductSalesEconomicsSnapshot | None:
        """Вернуть historical snapshot или None при отсутствии данных."""
        ...
