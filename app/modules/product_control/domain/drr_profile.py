"""Фабрика DrrProfile и валидация существующих экземпляров."""

from __future__ import annotations

from decimal import Decimal

from app.modules.product_control.domain.invariants_drr import (
    DrrProfileInvariantError,
    validate_drr_profile_fields,
)
from app.modules.product_control.domain.models import DrrProfile

__all__ = [
    "DrrProfileInvariantError",
    "drr_profile_from_percent",
    "validate_drr_profile",
    "validate_drr_profile_fields",
]


def validate_drr_profile(profile: DrrProfile) -> None:
    """Проверить уже созданный DrrProfile (идемпотентно с __post_init__)."""
    validate_drr_profile_fields(profile.target_drr_percent, profile.max_drr_percent)


def drr_profile_from_percent(
    target: Decimal | float | int,
    max_drr: Decimal | float | int,
) -> DrrProfile:
    """Сконструировать DrrProfile (валидация в __post_init__)."""
    return DrrProfile(
        target_drr_percent=Decimal(str(target)),
        max_drr_percent=Decimal(str(max_drr)),
    )
