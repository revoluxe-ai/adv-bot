from dataclasses import dataclass


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
    min_bid: int
    auto_max_bid: float | None