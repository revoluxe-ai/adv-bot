from enum import Enum


class ProductSearchTextsRequestTopOrderBy(str, Enum):
    ADDTOCART = "addToCart"
    CARTTOORDER = "cartToOrder"
    OPENCARD = "openCard"
    OPENTOCART = "openToCart"
    ORDERS = "orders"

    def __str__(self) -> str:
        return str(self.value)
