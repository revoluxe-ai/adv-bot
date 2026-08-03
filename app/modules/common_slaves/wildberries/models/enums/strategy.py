from enum import StrEnum


class Strategy(StrEnum):
    MIN_CPO = "MIN_CPO"
    OPTIMUM = "OPTIMUM"
    MAX_CONV = "MAX_CONV"
