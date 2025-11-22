from pydantic import BaseModel
from datetime import date

class KeywordPosition(BaseModel):
    nmid: int
    text: str
    date: date
    average_position: float
    orders: int
    total_views_avr_for_day: int

