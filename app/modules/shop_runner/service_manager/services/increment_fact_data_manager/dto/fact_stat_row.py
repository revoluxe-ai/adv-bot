from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class FactStatRow:
    bucket_start: datetime
    shop_id: UUID
    complex_adv_id: int
    views_adv_sum: int
    clicks_adv_sum: int
    carts_adv_sum: int
    orders_adv_sum: int
    spend_adv_sum_rub: int
    orders_sum_adv_rub: int
    open_card_sum: int
    carts_card_sum: int
    orders_card_sum: int
    orders_sum_card_rub: int
    buy_outs_sum: int
    src_ts: datetime
    version: int
