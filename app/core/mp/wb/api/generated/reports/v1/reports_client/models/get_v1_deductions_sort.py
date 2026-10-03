from enum import Enum


class GetV1DeductionsSort(str, Enum):
    BONUSSUMM = "bonusSumm"
    DTBONUS = "dtBonus"
    NMID = "nmId"

    def __str__(self) -> str:
        return str(self.value)
