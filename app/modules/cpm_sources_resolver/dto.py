"""DTO for resolved current bid (CPM) with optional timestamp and source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CpmBidSource = Literal["set_bid", "api", "bid_log", "stats"]


@dataclass(frozen=True)
class CurrentBidDTO:
    """Resolved current bid per norm_query with optional source timestamp."""

    text: str
    bid: int
    timestamp: datetime | None
    source: CpmBidSource = "stats"
