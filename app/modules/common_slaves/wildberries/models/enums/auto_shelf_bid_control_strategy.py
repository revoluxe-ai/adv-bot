from enum import StrEnum, auto

class AutoShelfBidControlStrategy(StrEnum):
    CYCLE_METRIC = "cycle_metric"
    PLAN_DISTANCE = "plan_distance"
