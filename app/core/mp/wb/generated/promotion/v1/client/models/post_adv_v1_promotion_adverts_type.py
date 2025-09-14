from enum import IntEnum


class PostAdvV1PromotionAdvertsType(IntEnum):
    VALUE_4 = 4
    VALUE_5 = 5
    VALUE_6 = 6
    VALUE_7 = 7
    VALUE_8 = 8

    def __str__(self) -> str:
        return str(self.value)
