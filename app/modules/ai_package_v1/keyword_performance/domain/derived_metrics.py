"""Deterministic derived metrics: ratios 0..1, finite JSON only."""

from __future__ import annotations

import math


def safe_ratio(numerator: int | float | None, denominator: int | float | None) -> float | None:
    """Ratio in 0..1; null when denominator missing or zero."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    value = float(numerator) / float(denominator)
    if not math.isfinite(value):
        return None
    return value


def safe_cpo(spend: float | None, orders: int | None, *, spend_factual: bool) -> float | None:
    """CPO only when spend is FACTUAL and orders > 0."""
    if not spend_factual or spend is None or orders is None or orders <= 0:
        return None
    value = spend / float(orders)
    if not math.isfinite(value):
        return None
    return value


def finite_or_none(value: float | int | None) -> float | None:
    """Reject NaN/Infinity for JSON export."""
    if value is None:
        return None
    f = float(value)
    if not math.isfinite(f):
        return None
    return f
