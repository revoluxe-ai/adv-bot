from dataclasses import dataclass
from datetime import datetime

"""
{"data":[{"nmID":302872270,"imtName":"Крабик для волос набор 20 шт",
"vendorCode":"444combclear",
"history":[{"dt":"2025-02-27",
"openCardCount":754,
"addToCartCount":50,
"addToCartConversion":7,
"ordersCount":9,
"ordersSumRub":5203,
"cartToOrderConversion":18,
"buyoutsCount":1,
"buyoutsSumRub":580,
"buyoutPercent":100},
{"dt":"2025-02-28",
"openCardCount":699,
"addToCartCount":55,
"addToCartConversion":8,
"ordersCount":9,
"ordersSumRub":5220,
"cartToOrderConversion":16,
"buyoutsCount":1,
"buyoutsSumRub":580,
"buyoutPercent":100},
{"dt":"2025-03-01",
"openCardCount":599
,"addToCartCount":43,
"addToCartConversion":7,"
ordersCount":12,
"ordersSumRub":6925,
"cartToOrderConversion":28,
"buyoutsCount":0,
"buyoutsSumRub":0,
"buyoutPercent":0}]}],
"error":false,
"errorText":"",
"additionalErrors":null}

"""


@dataclass
class CommonStat:
    nmid: int
    date: datetime
    open_card: int
    add_to_cart: int
    orders: int
    orders_sum: float
    buy_outs: int
