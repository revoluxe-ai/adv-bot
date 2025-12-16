from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType


class GetMinBidsCommandItem(BaseModel):
    adv_id: int
    nmids: list[int]
    placement_type: AdvPlacementType

    model_config = ConfigDict(arbitrary_types_allowed=True)


class GetMinBidsCommand(BaseModel):
    items: list[GetMinBidsCommandItem]

    model_config = ConfigDict(arbitrary_types_allowed=True)
















