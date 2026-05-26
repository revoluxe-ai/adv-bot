"""DB field ``aggressiveness``: 1 = min, 2 = mid, 3 = max (default)."""

from __future__ import annotations

from enum import IntEnum


class V3RolloutAggressiveness(IntEnum):
    MIN = 1
    MID = 2
    MAX = 3


def normalize_v3_rollout_aggressiveness(raw: int | None) -> V3RolloutAggressiveness:
    if raw is None:
        return V3RolloutAggressiveness.MAX
    if raw < 1:
        return V3RolloutAggressiveness.MIN
    if raw > 3:
        return V3RolloutAggressiveness.MAX
    return V3RolloutAggressiveness(raw)
