from enum import IntEnum


class OfficeDeliveryType(IntEnum):
    VALUE_1 = 1
    VALUE_2 = 2
    VALUE_3 = 3
    VALUE_5 = 5
    VALUE_6 = 6

    def __str__(self) -> str:
        return str(self.value)
