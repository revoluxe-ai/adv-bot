from enum import Enum


class TableGroupField(str, Enum):
    AVGORDERS = "avgOrders"
    AVGSTOCKTURNOVER = "avgStockTurnover"
    BUYOUTCOUNT = "buyoutCount"
    BUYOUTPERCENT = "buyoutPercent"
    BUYOUTSUM = "buyoutSum"
    FROMCLIENTCOUNT = "fromClientCount"
    LOSTBUYOUTSCOUNT = "lostBuyoutsCount"
    LOSTBUYOUTSSUM = "lostBuyoutsSum"
    LOSTORDERSCOUNT = "lostOrdersCount"
    LOSTORDERSSUM = "lostOrdersSum"
    MAXPRICE = "maxPrice"
    MINPRICE = "minPrice"
    OFFICEMISSINGTIME = "officeMissingTime"
    ORDERSCOUNT = "ordersCount"
    ORDERSSUM = "ordersSum"
    SALERATE = "saleRate"
    STOCKCOUNT = "stockCount"
    STOCKSUM = "stockSum"
    TOCLIENTCOUNT = "toClientCount"

    def __str__(self) -> str:
        return str(self.value)
