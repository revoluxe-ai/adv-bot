from enum import Enum


class GetApiV1AnalyticsBannedProductsShadowedSort(str, Enum):
    BRAND = "brand"
    NMID = "nmId"
    NMRATING = "nmRating"
    TITLE = "title"
    VENDORCODE = "vendorCode"

    def __str__(self) -> str:
        return str(self.value)
