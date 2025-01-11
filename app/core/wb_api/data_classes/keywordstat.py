from datetime import datetime

from pydantic import BaseModel, Field


class KeywordStat(BaseModel):
    text: str = Field(..., title='keyword')
    views: int = Field(..., title='views')
    clicks: int = Field(..., title='clicks')
    spend: float = Field(..., title='sum')
    adv_id: int = Field(..., title='adv_id')
    update_timestamp: datetime
    date: datetime


