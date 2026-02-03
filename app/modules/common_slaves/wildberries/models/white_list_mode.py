from enum import StrEnum, auto


class WhiteListMode(StrEnum):
    ACTIVE_ONLY_WHITE_LIST = auto()
    TAIL_TRIMMING = auto()
    ABOVE_MIN_RATING = auto()
