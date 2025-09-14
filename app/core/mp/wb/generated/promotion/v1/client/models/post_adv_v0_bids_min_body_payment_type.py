from enum import Enum


class PostAdvV0BidsMinBodyPaymentType(str, Enum):
    CPC = "cpc"
    CPM = "cpm"

    def __str__(self) -> str:
        return str(self.value)
