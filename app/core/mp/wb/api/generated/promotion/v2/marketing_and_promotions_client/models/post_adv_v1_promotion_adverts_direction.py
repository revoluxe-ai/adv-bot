from enum import Enum


class PostAdvV1PromotionAdvertsDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"

    def __str__(self) -> str:
        return str(self.value)
