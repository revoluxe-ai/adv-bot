import datetime
from pydantic import BaseModel

class CommonCardStat(BaseModel):
    nmid: int
    open_card: int
    add_to_cart: int
    orders: int
    orders_sum: int
    buy_outs: int
    date: datetime.datetime

