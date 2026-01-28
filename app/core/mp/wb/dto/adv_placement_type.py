from __future__ import annotations

from enum import Enum

from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PlacementType,
    PostApiAdvertV1BidsMinBodyPlacementTypesItem,
)


class AdvPlacementType(str, Enum):
    """Доменный тип размещения для запросов минимальных ставок."""

    AUTO_ADV = "auto_adv"
    SEARCH_ADV = "search_adv"
    RECOMMENDATION = 'recommendation'

    def to_wb_placement_type(self) -> PostApiAdvertV1BidsMinBodyPlacementTypesItem:
        match self:
            case AdvPlacementType.AUTO_ADV:
                return PostApiAdvertV1BidsMinBodyPlacementTypesItem.COMBINED
            case AdvPlacementType.SEARCH_ADV:
                return PostApiAdvertV1BidsMinBodyPlacementTypesItem.SEARCH
            case _:
                raise ValueError(f"Unsupported placement type {self}")

    @classmethod
    def from_wb_placement_type(cls, placement_type: PlacementType) -> AdvPlacementType:
        match placement_type:
            case PlacementType.COMBINED:
                return cls.AUTO_ADV
            case PlacementType.SEARCH:
                return cls.SEARCH_ADV
            case PlacementType.RECOMMENDATION:
                return cls.RECOMMENDATION
            case _:
                raise ValueError(f"Unsupported WB placement type {placement_type}")
