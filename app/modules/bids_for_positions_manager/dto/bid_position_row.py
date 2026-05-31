"""DTO for normalized bid position row (no conv)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BidPositionRow:
    """Single bid position from CH / normalization.

    ``ch_observed=False`` — синтетическая строка ``_fill_positions``, не bucket CH.
    """

    keyword: str
    position: int
    bid: int  # стоимость 1000 показов
    timestamp: datetime
    ch_observed: bool = True
