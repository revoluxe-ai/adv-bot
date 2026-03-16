"""DTO for resolved current bid (CPM) with optional timestamp."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CurrentBidDTO:
    """Resolved current bid per norm_query with optional source timestamp."""

    text: str
    bid: int
    timestamp: datetime | None
