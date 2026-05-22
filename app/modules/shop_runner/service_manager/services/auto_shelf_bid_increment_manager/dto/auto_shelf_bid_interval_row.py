"""Строка для INSERT в default_db.auto_shelf_bid_intervals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class AutoShelfBidIntervalRow:
    """Один инкрементальный интервал: контекст (bid, price, mode) + дельты метрик."""

    event_date: date
    event_id: str
    src_ts: datetime
    bucket_start: datetime
    version: int
    nmid: int
    mode: str
    bid_minor: int
    currency: str
    price_minor: int | None
    price_currency: str
    delta_impressions: int
    delta_clicks: int
    delta_carts: int
    delta_orders: int
    delta_spend: float
