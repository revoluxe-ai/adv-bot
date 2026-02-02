
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvCommonStat:
    views_adv_sum: int
    clicks_adv_sum: int
    carts_adv_sum: int
    orders_adv_sum: int
    spend_adv_sum_rub: int
    orders_sum_adv_rub: int
