from enum import Enum


class GetAdvV0AuctionAdvertsPaymentType(str, Enum):
    CPC = "cpc"
    CPM = "cpm"

    def __str__(self) -> str:
        return str(self.value)
