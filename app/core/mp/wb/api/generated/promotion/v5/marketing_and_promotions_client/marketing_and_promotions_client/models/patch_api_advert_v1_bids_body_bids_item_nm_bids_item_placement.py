from enum import Enum


class PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement(str, Enum):
    COMBINED = "combined"
    RECOMMENDATIONS = "recommendations"
    SEARCH = "search"

    def __str__(self) -> str:
        return str(self.value)
