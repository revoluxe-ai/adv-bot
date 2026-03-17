"""DTO for all CPM sources per text (set_bid, api, bid_log) for UI and cascade."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AllCpmSourcesPerText:
    """All CPM sources per text (set_bid, api, bid_log) for UI and cascade. Stats from cluster_stat in manager."""

    text: str
    cpm_set_bid: int | None = None
    cpm_set_bid_date: datetime | None = None
    cpm_from_api: int | None = None
    cpm_from_bid_log: float | None = None
    cpm_from_bid_log_date: datetime | None = None
