"""
Чистый расчёт target/max CPO из DrrProfile и effective product price.

Единственное место формулы DRR→CPO в домене product control.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.modules.product_control.domain.enums import ProductControlBlockerReason
from app.modules.product_control.domain.money import MONEY_QUANT_RUB
from app.modules.product_control.domain.models import (
    DerivedCpoRub,
    DrrProfile,
    ProductCpoBlocked,
    ProductCpoResult,
    ProductCpoSuccess,
)


class ProductCpoResolver:
    """DRR profile + effective unit price → canonical CPO в рублях (0.01)."""

    @staticmethod
    def resolve(
        profile: DrrProfile,
        effective_product_price_rub: Decimal | None,
    ) -> ProductCpoResult:
        """
        Вычислить target/max CPO.

        Args:
            profile: Эффективный атомарный DrrProfile.
            effective_product_price_rub: Текущая/эффективная цена; ``None`` → blocked.

        Returns:
            ProductCpoSuccess или ProductCpoBlocked (без подстановки нуля).
        """
        if effective_product_price_rub is None:
            return ProductCpoBlocked(
                reason=ProductControlBlockerReason.BLOCKED_BY_PRODUCT_PRICE_SOURCE,
            )
        if effective_product_price_rub <= Decimal("0"):
            return ProductCpoBlocked(
                reason=ProductControlBlockerReason.BLOCKED_BY_PRODUCT_PRICE_SOURCE,
            )

        target = ProductCpoResolver._cpo_from_percent(
            effective_product_price_rub,
            profile.target_drr_percent,
        )
        max_cpo = ProductCpoResolver._cpo_from_percent(
            effective_product_price_rub,
            profile.max_drr_percent,
        )
        return ProductCpoSuccess(cpo=DerivedCpoRub(target_cpo_rub=target, max_cpo_rub=max_cpo))

    @staticmethod
    def _cpo_from_percent(price_rub: Decimal, drr_percent: Decimal) -> Decimal:
        raw = price_rub * drr_percent / Decimal("100")
        return raw.quantize(MONEY_QUANT_RUB, rounding=ROUND_HALF_UP)
