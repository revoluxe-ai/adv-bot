from __future__ import annotations

from enum import IntEnum


class BalanceLevel(IntEnum):
    EXPIRED = 0
    D1 = 1
    D3 = 3


def pick_level(days_left: float) -> BalanceLevel | None:
    if days_left <= 0:
        return BalanceLevel.EXPIRED
    if days_left <= 1:
        return BalanceLevel.D1
    if days_left <= 3:
        return BalanceLevel.D3
    return None

