from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FullAdvStat:
    campaign_id: int
    date: datetime
    views: int
    clicks: int
    ctr: float
    cpc: float
    spend: float
    orders: int
    cr: float
    revenue: float
    drr: float
    shop_id: Optional[int] = None 