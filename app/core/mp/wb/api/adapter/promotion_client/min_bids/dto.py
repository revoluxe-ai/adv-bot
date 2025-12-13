from __future__ import annotations

from dataclasses import dataclass

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType


@dataclass
class MinBidForNmid:
    nmid: int
    placement_type: AdvPlacementType
    min_cpm: int
















