from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SalesFunnelProductsHistoryCommand:
    nmids: list[int]
    start: date
    end: date
    aggregation_level: str = "day"
    skip_deleted_nm: bool = True


