from enum import Enum


class PostAdvV1PromotionAdvertsOrder(str, Enum):
    CHANGE = "change"
    CREATE = "create"
    ID = "id"

    def __str__(self) -> str:
        return str(self.value)
