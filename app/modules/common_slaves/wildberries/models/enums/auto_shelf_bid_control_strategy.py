from enum import StrEnum


class AutoShelfBidControlStrategy(StrEnum):
    """User-facing main-bid strategies for auto shelf bid control."""

    CYCLE_METRIC = "cycle_metric"
    PLAN_DISTANCE = "plan_distance"
    CTR = "ctr"
    CPC = "cpc"
