from enum import Enum


class PostAdvV2SeacatSaveAdBodyBidType(str, Enum):
    MANUAL = "manual"
    UNIFIED = "unified"

    def __str__(self) -> str:
        return str(self.value)
