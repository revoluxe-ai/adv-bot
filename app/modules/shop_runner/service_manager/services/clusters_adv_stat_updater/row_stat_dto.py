from datetime import date

from pydantic import BaseModel


class RowStatDTO(BaseModel):
    adv_id: int
    nmid: int
    wb_category: str
    norm_query: str
    views: int
    clicks: int
    ctr: float
    cpm: float | None
    add_to_cart: int | None
    orders: int
    cpc: float | None
    avr_pos: float | None
    date: date

