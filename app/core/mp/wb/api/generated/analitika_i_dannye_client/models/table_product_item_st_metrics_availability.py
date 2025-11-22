from enum import Enum


class TableProductItemStMetricsAvailability(str, Enum):
    ACTUAL = "actual"
    BALANCED = "balanced"
    DEFICIENT = "deficient"
    INVALIDDATA = "invalidData"
    NONACTUAL = "nonActual"
    NONLIQUID = "nonLiquid"

    def __str__(self) -> str:
        return str(self.value)
