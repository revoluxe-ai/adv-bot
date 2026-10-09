"""Инварианты DrrProfile без зависимости от models (избегаем циклических импортов)."""

from __future__ import annotations

from decimal import Decimal


class DrrProfileInvariantError(ValueError):
    """Нарушение инвариантов DrrProfile при создании или записи."""


def validate_drr_profile_fields(
    target_drr_percent: Decimal,
    max_drr_percent: Decimal,
) -> None:
    """
    Проверить инварианты DRR-процентов.

    Raises:
        DrrProfileInvariantError: target < 0 или max < target.
    """
    if target_drr_percent < Decimal("0"):
        raise DrrProfileInvariantError("target_drr_percent must be non-negative")
    if max_drr_percent < target_drr_percent:
        raise DrrProfileInvariantError(
            "max_drr_percent must be >= target_drr_percent"
        )
