from typing import Any

from pydantic import BaseModel

class NormqueryStatsDTO(BaseModel):
    adv_id: int
    nmid: int
    norm_query: str
    views: int
    clicks: int
    ctr: float
    cpm: float | None
    add_to_cart: int | None
    orders: int
    cpc: float | None
    avr_pos: float | None
    add_keys: list[str]
    add_properties: dict[str, Any]
