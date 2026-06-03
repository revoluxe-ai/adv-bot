"""Вид ступени лестницы V3 для ``KeywordV3LadderState``."""

from __future__ import annotations

from enum import Enum


class V3LadderStageKind(str, Enum):
    """Ступень: M/O/C, OFF или GAP (NO DATA без PFO и без CH-профиля)."""

    MIN_CPA = "min_cpa"
    OPTIMUM = "optimum"
    MAX_CONVERSION = "max_conversion"
    OFF = "off"
    GAP = "gap"
