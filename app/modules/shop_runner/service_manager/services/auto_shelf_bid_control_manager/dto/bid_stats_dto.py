"""DTO агрегированной статистики по ставке/режиму для control-контура."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BidStatsDTO:
    """Агрегированные метрики для пары bid+mode за выбранный период."""

    bid_minor: int
    currency: str
    mode: str | None
    last_interval_at: datetime | None
    impressions: int
    clicks: int
    carts: int
    orders: int
    spend: float
    cart_cpa: float | None  # transition v1: используется как CPC score-слот
    ctr: float | None
    cart_cr: float | None

