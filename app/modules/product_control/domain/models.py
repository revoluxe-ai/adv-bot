"""Базовые value-типы: ProductRef, DrrProfile, результаты резолверов."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.product_control.domain.invariants_drr import (
    DrrProfileInvariantError,
    validate_drr_profile_fields,
)
from app.modules.product_control.domain.enums import (
    DrrResolutionTier,
    EffectiveControlOutcomeKind,
    ProductControlBlockerReason,
)


@dataclass(frozen=True, slots=True)
class ProductRef:
    """Каноническая идентичность mutable product control."""

    shop_id: str
    nmid: int

    def __post_init__(self) -> None:
        if not self.shop_id:
            raise ValueError("shop_id must be non-empty")
        if self.nmid <= 0:
            raise ValueError("nmid must be positive")


@dataclass(frozen=True, slots=True)
class DrrProfile:
    """
    Атомарный DRR-профиль: оба поля обязательны на хранении.

    Инвариант: ``max_drr_percent >= target_drr_percent``.
    """

    target_drr_percent: Decimal
    max_drr_percent: Decimal

    def __post_init__(self) -> None:
        try:
            validate_drr_profile_fields(
                self.target_drr_percent,
                self.max_drr_percent,
            )
        except DrrProfileInvariantError:
            raise
        except (TypeError, ValueError) as exc:
            raise DrrProfileInvariantError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class DerivedCpoRub:
    """Канонический выход ProductCpoResolver (0.01 RUB, уже округлён)."""

    target_cpo_rub: Decimal
    max_cpo_rub: Decimal


@dataclass(frozen=True, slots=True)
class EffectiveControlSuccess:
    """Успешное разрешение effective control."""

    kind: EffectiveControlOutcomeKind
    profile: DrrProfile | None = None
    tier: DrrResolutionTier | None = None


@dataclass(frozen=True, slots=True)
class EffectiveControlBlocked:
    """Fail-closed исход effective control."""

    kind: EffectiveControlOutcomeKind
    reason: ProductControlBlockerReason


EffectiveControlResult = EffectiveControlSuccess | EffectiveControlBlocked


@dataclass(frozen=True, slots=True)
class ProductCpoSuccess:
    """Успешный расчёт CPO из DRR и effective price."""

    cpo: DerivedCpoRub


@dataclass(frozen=True, slots=True)
class ProductCpoBlocked:
    """Блокировка расчёта CPO (цена или политика)."""

    reason: ProductControlBlockerReason


ProductCpoResult = ProductCpoSuccess | ProductCpoBlocked
