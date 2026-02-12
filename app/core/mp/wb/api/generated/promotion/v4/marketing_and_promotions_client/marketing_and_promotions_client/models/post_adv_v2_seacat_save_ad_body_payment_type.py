from enum import Enum


class PostAdvV2SeacatSaveAdBodyPaymentType(str, Enum):
    CPC = "cpc"
    CPM = "cpm"

    def __str__(self) -> str:
        return str(self.value)
