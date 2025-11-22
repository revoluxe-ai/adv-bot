from enum import Enum


class PositionCluster(str, Enum):
    ALL = "all"
    BELOW = "below"
    FIRSTHUNDRED = "firstHundred"
    SECONDHUNDRED = "secondHundred"

    def __str__(self) -> str:
        return str(self.value)
