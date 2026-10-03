from enum import Enum


class OrdersItemWarehouseType(str, Enum):
    СКЛАД_WB = "Склад WB"
    СКЛАД_ПРОДАВЦА = "Склад продавца"

    def __str__(self) -> str:
        return str(self.value)
