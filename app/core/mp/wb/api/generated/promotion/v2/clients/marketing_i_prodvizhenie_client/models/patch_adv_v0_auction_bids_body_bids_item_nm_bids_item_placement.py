from enum import Enum


class PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement(str, Enum):
    COMBINED = "combined"
    RECOMMENDATIONS = "recommendations"
    SEARCH = "search"

    def __str__(self) -> str:
        return str(self.value)
