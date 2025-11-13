from enum import Enum


class GetAdvV0AuctionAdvertsStatuses(str, Enum):
    VALUE_0 = "-1"
    VALUE_1 = "4"
    VALUE_2 = "7"
    VALUE_3 = "8"
    VALUE_4 = "9"
    VALUE_5 = "11"

    def __str__(self) -> str:
        return str(self.value)
