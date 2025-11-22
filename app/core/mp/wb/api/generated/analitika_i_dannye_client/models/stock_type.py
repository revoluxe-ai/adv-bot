from enum import Enum


class StockType(str, Enum):
    MP = "mp"
    VALUE_0 = ""
    WB = "wb"

    def __str__(self) -> str:
        return str(self.value)
