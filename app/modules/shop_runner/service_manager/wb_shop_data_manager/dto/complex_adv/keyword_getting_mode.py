from enum import StrEnum, auto


class KeywordGettingMode(StrEnum):
    ONLY_ACTIVE_KEYWORDS = auto()
    ALL_KEYWORDS = auto()