from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .update_bids_command import DirectEnum


@dataclass(frozen=True)
class CalculationInput:
    adv_id: int
    nmid: int
    cluster: str
    current_bid: int
    current_position: float
    target_position: int
    step: int
    max_bid: int
    min_bid: int | None
    predict_target_bids: dict[str, dict[int, int]] | None
    prev_direct: "DirectEnum | None" = None
    prev_step: int | None = None
