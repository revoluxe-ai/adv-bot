from enum import IntEnum


class GetAdvV0AuctionAdvertsStatuses(IntEnum):
    VALUE_NEGATIVE_1 = -1
    VALUE_4 = 4
    VALUE_7 = 7
    VALUE_8 = 8
    VALUE_9 = 9
    VALUE_11 = 11

    def __str__(self) -> str:
        return str(self.value)
