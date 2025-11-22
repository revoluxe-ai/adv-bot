from enum import Enum


class OrderByGrTeField(str, Enum):
    ADDTOCART = "addToCart"
    AVGPOSITION = "avgPosition"
    CARTTOORDER = "cartToOrder"
    OPENCARD = "openCard"
    OPENTOCART = "openToCart"
    ORDERS = "orders"
    VISIBILITY = "visibility"

    def __str__(self) -> str:
        return str(self.value)
