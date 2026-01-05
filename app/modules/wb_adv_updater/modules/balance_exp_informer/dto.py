from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReminderItem:
    reminder_id: int
    wb_cabinet_id: int
    shop_id: str
    shop_name: str
    level: int
    balance: float
    avg_daily_spend: float
    days_left: float

