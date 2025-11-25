from enum import Enum


class OrderByField(str, Enum):
    ADDTOCART = "addToCart"
    ADDTOWISHLIST = "addToWishlist"
    AVGPRICE = "avgPrice"
    BUYOUTCOUNT = "buyoutCount"
    BUYOUTSUM = "buyoutSum"
    CANCELCOUNT = "cancelCount"
    CANCELSUM = "cancelSum"
    LOCALIZATIONPERCENT = "localizationPercent"
    OPENCARD = "openCard"
    ORDERCOUNT = "orderCount"
    ORDERSUM = "orderSum"
    SHAREORDERPERCENT = "shareOrderPercent"
    STOCKMPQTY = "stockMpQty"
    STOCKWBQTY = "stockWbQty"
    TIMETOREADY = "timeToReady"
    WBCLUB_AVGORDERCOUNTPERDAY = "wbClub.avgOrderCountPerDay"
    WBCLUB_AVGPRICE = "wbClub.avgPrice"
    WBCLUB_BUYOUTCOUNT = "wbClub.buyoutCount"
    WBCLUB_BUYOUTPERCENT = "wbClub.buyoutPercent"
    WBCLUB_BUYOUTSUM = "wbClub.buyoutSum"
    WBCLUB_CANCELCOUNT = "wbClub.cancelCount"
    WBCLUB_CANCELSUM = "wbClub.cancelSum"
    WBCLUB_ORDERCOUNT = "wbClub.orderCount"
    WBCLUB_ORDERSUM = "wbClub.orderSum"

    def __str__(self) -> str:
        return str(self.value)
