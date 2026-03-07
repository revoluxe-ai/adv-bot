"""DTO for normalized bid position row (no conv)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BidPositionRow:
    """Single bid position from CH / normalization: keyword, position, bid, timestamp only."""

    keyword: str
    position: int
    bid: int  # стоимость 1000 показов
    timestamp: datetime
