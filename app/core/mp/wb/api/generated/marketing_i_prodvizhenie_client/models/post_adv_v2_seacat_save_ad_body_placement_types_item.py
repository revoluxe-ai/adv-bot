from enum import Enum


class PostAdvV2SeacatSaveAdBodyPlacementTypesItem(str, Enum):
    RECOMMENDATIONS = "recommendations"
    SEARCH = "search"

    def __str__(self) -> str:
        return str(self.value)
