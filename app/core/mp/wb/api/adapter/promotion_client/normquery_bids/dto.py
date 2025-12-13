from __future__ import annotations

from pydantic import BaseModel


class NormqueryBidDTO(BaseModel):
    advert_id: int
    nm_id: int
    norm_query: str
    bid: int
