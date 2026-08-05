from enum import Enum


class ExciseReportRequestCountriesItem(str, Enum):
    AM = "AM"
    BY = "BY"
    KG = "KG"
    KZ = "KZ"
    RU = "RU"
    UZ = "UZ"

    def __str__(self) -> str:
        return str(self.value)
