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


@dataclass(frozen=True)
class AllCpmSourcesPerText:
    """All CPM sources per text (set_bid, api, bid_log) for UI and cascade. Stats from cluster_stat in manager."""

    text: str
    cpm_set_bid: int | None = None
    cpm_set_bid_date: datetime | None = None
    cpm_from_api: int | None = None
    cpm_from_bid_log: float | None = None
    cpm_from_bid_log_date: datetime | None = None
