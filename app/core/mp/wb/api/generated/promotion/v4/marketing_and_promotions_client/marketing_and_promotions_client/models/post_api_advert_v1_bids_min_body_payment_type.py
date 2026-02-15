from enum import Enum


class PostApiAdvertV1BidsMinBodyPaymentType(str, Enum):
    CPC = "cpc"
    CPM = "cpm"

    def __str__(self) -> str:
        return str(self.value)
