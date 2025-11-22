from enum import Enum


class AvailabilityFiltersItem(str, Enum):
    ACTUAL = "actual"
    BALANCED = "balanced"
    DEFICIENT = "deficient"
    INVALIDDATA = "invalidData"
    NONACTUAL = "nonActual"
    NONLIQUID = "nonLiquid"

    def __str__(self) -> str:
        return str(self.value)
