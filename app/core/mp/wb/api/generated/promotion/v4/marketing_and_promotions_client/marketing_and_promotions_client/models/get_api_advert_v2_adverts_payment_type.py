from enum import Enum


class GetApiAdvertV2AdvertsPaymentType(str, Enum):
    CPC = "cpc"
    CPM = "cpm"

    def __str__(self) -> str:
        return str(self.value)
