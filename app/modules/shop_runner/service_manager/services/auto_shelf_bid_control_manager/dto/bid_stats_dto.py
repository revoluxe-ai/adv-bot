"""DTO агрегированной статистики по ставке/режиму для control-контура."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BidStatsDTO:
    """Агрегированные метрики для пары bid+mode за выбранный период."""

    bid_minor: int
    currency: str
    mode: str | None
    impressions: int
    clicks: int
    carts: int
    orders: int
    spend: float
    cart_cpa: float | None
    ctr: float | None
    cart_cr: float | None

