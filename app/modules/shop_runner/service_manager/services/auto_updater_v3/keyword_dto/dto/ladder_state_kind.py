"""Вид ступени лестницы V3 для ``KeywordV3LadderState``."""

from __future__ import annotations

from enum import Enum


class V3LadderStageKind(str, Enum):
    """Ступени ladder-state: OFF, GAP (NO DATA без CH), MIN/OPT/MAX."""

    OFF = "OFF"
    GAP = "GAP"
    MIN_CPA = "MIN_CPA"
    OPTIMUM = "OPTIMUM"
    MAX_CONVERSION = "MAX_CONVERSION"


# Legacy alias
LadderStateKind = V3LadderStageKind
