from enum import StrEnum, auto


class Strategy(StrEnum):
    MIN_CPO = "MIN_CPO"
    OPTIMUM = "OPTIMUM"
    MAX_CONV = "MAX_CONV"
