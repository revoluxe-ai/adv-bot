"""
Минимальная требуемая sufficiency наблюдаемых метрик для CPO policy.

Bounded vocabulary; unknown значения fail closed при валидации payload.
"""

from __future__ import annotations

from enum import StrEnum


class MinObservedDataSufficiencyRequirement(StrEnum):
    """
    Минимальный уровень ``DataSufficiency`` фактических метрик для действия policy.

    V1: только ``SUFFICIENT`` (строгий контракт без неутверждённых порогов).
    """

    SUFFICIENT = "SUFFICIENT"


def validate_min_observed_requirement(
    value: MinObservedDataSufficiencyRequirement,
) -> None:
    """Fail closed на неизвестных членах enum (defensive)."""
    if value not in MinObservedDataSufficiencyRequirement:
        raise ValueError(f"unknown min observed data sufficiency: {value!r}")

