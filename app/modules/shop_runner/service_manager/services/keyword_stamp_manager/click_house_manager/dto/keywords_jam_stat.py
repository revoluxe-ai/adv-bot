from datetime import datetime

from pydantic import BaseModel


class KeywordJamStat(BaseModel):
    nmid: int
    keyword_text: str
    position: float
    timestamp: datetime
    adv_id: int
    adv_type: int
    total_views: int
    total_orders: int
