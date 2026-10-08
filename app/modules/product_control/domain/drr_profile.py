"""Валидация и инварианты DrrProfile."""

from __future__ import annotations

from decimal import Decimal

from app.modules.product_control.domain.models import DrrProfile


class DrrProfileInvariantError(ValueError):
    """Нарушение инвариантов DrrProfile при создании или записи."""


def validate_drr_profile(profile: DrrProfile) -> None:
    """
    Проверить полноту и порядок процентов DRR.

    Raises:
        DrrProfileInvariantError: target/max отсутствуют логически или max < target.
    """
    if profile.target_drr_percent < Decimal("0"):
        raise DrrProfileInvariantError("target_drr_percent must be non-negative")
    if profile.max_drr_percent < profile.target_drr_percent:
        raise DrrProfileInvariantError(
            "max_drr_percent must be >= target_drr_percent"
        )


def drr_profile_from_percent(
    target: Decimal | float | int,
    max_drr: Decimal | float | int,
) -> DrrProfile:
    """Сконструировать DrrProfile с немедленной валидацией."""
    profile = DrrProfile(
        target_drr_percent=Decimal(str(target)),
        max_drr_percent=Decimal(str(max_drr)),
    )
    validate_drr_profile(profile)
    return profile
