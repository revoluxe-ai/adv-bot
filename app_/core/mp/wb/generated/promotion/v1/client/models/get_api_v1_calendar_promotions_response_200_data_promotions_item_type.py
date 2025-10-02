from enum import Enum


class GetApiV1CalendarPromotionsResponse200DataPromotionsItemType(str, Enum):
    AUTO = "auto"
    REGULAR = "regular"

    def __str__(self) -> str:
        return str(self.value)
