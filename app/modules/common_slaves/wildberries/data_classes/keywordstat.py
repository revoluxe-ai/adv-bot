from dataclasses import dataclass
from datetime import datetime


@dataclass
class KeywordStat:
    text: str
    views: int
    clicks: int
    spend: float
    adv_id: int
    update_timestamp: datetime
    date: datetime
