from enum import Enum


class PlacementType(str, Enum):
    COMBINED = "combined"
    RECOMMENDATION = "recommendation"
    SEARCH = "search"

    def __str__(self) -> str:
        return str(self.value)
