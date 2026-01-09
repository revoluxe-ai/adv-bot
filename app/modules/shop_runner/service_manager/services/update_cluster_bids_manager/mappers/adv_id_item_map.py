from dataclasses import dataclass


@dataclass(frozen=True)
class AdvIdItemCalculateData:
    adv_id: int
    nmid: int
    cluster: str
    current_position: float
    target_position: int
    max_cpm: int
    step: int
    current_cpm: int | None