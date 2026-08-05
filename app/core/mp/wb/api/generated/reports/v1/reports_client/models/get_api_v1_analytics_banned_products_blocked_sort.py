from enum import Enum


class GetApiV1AnalyticsBannedProductsBlockedSort(str, Enum):
    BRAND = "brand"
    NMID = "nmId"
    REASON = "reason"
    TITLE = "title"
    VENDORCODE = "vendorCode"

    def __str__(self) -> str:
        return str(self.value)
