from enum import IntEnum


class KeywordStrategyMode(IntEnum):
    """Stored on KeywordSetting.strategy_mode as integer."""

    OFF = 0
    MIN_CPA = 1
    OPTIMUM = 2
    MAX_CONVERSION = 3
