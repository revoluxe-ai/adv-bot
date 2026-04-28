from enum import Enum


class AdvertSettingsPaymentType(str, Enum):
    CPC = "cpc"
    CPM = "cpm"

    def __str__(self) -> str:
        return str(self.value)
