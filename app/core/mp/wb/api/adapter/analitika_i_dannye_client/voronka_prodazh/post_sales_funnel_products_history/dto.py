from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class CommonSaleStatRow:
    nmid: int
    day: date
    open_card: int
    add_to_cart: int
    orders: int
    orders_sum: float
    buy_outs: int


