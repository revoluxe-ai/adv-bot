from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class KeywordStamp:
    shop_id: str
    adv_id: int
    nmid: int
    text: str
    avr_position : float
    orders: int
    date: date
    total_views: int
    current_cpm: int
    timestamp: datetime