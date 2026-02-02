from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardCommonStat:
    open_card_sum: int
    carts_card_sum: int
    orders_card_sum: int
    orders_sum_card_rub: int
    buy_outs_sum: int