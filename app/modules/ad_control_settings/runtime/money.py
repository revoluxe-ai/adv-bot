"""Квантование денег и процентов V1 (0.01, ROUND_HALF_UP)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANT_RUB = Decimal("0.01")
PERCENT_QUANT = Decimal("0.01")


def quantize_rub(value: Decimal) -> Decimal:
    """Округлить сумму в рублях до копейки."""
    return value.quantize(MONEY_QUANT_RUB, rounding=ROUND_HALF_UP)


def quantize_percent(value: Decimal) -> Decimal:
    """Округлить процент (не долю) до 0.01 пункта."""
    return value.quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)
