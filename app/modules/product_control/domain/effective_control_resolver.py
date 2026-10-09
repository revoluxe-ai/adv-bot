"""
Чистый резолвер effective DRR / исхода enrollment (без I/O).

Матрица shop master gate — owner-contract.md § Effective enrollment matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.product_control.domain.enums import (
    DrrResolutionTier,
    EffectiveControlOutcomeKind,
    ProductControlBlockerReason,
    ProductControlMode,
    ShopControlEnrollment,
)
from app.modules.product_control.domain.models import (
    DrrProfile,
    EffectiveControlBlocked,
    EffectiveControlResult,
    EffectiveControlSuccess,
)


@dataclass(frozen=True, slots=True)
class EffectiveControlInput:
    """Входные настройки enrollment и профилей для одного ``(shop_id, nmid)``."""

    shop_enrollment: ShopControlEnrollment
    product_mode: ProductControlMode
    shop_profile: DrrProfile | None
    product_profile: DrrProfile | None


class EffectiveControlResolver:
    """
    Определяет LEGACY_NOT_ENROLLED, LEGACY tier, активный DrrProfile или blocked.

    Не смешивает поля профилей разных tier; наследование только целым профилем.
    """

    @staticmethod
    def resolve(settings: EffectiveControlInput) -> EffectiveControlResult:
        enrollment = settings.shop_enrollment
        mode = settings.product_mode

        if enrollment == ShopControlEnrollment.NOT_ENROLLED:
            return EffectiveControlSuccess(
                kind=EffectiveControlOutcomeKind.LEGACY_NOT_ENROLLED,
            )

        if enrollment == ShopControlEnrollment.BLOCKED:
            return EffectiveControlBlocked(
                kind=EffectiveControlOutcomeKind.PRODUCT_CONTROL_BLOCKED,
                reason=ProductControlBlockerReason.SHOP_CONTROL_BLOCKED,
            )

        # ENROLLED
        if mode == ProductControlMode.BLOCKED:
            return EffectiveControlBlocked(
                kind=EffectiveControlOutcomeKind.PRODUCT_CONTROL_BLOCKED,
                reason=ProductControlBlockerReason.PRODUCT_CONTROL_BLOCKED,
            )

        if mode == ProductControlMode.OVERRIDE_ENABLED:
            if settings.product_profile is None:
                return EffectiveControlBlocked(
                    kind=EffectiveControlOutcomeKind.INVALID_CONFIGURATION,
                    reason=ProductControlBlockerReason.INVALID_CONFIGURATION,
                )
            return EffectiveControlSuccess(
                kind=EffectiveControlOutcomeKind.ACTIVE_DRR_PROFILE,
                profile=settings.product_profile,
                tier=DrrResolutionTier.PRODUCT,
            )

        # INHERIT_SHOP
        if settings.shop_profile is not None:
            return EffectiveControlSuccess(
                kind=EffectiveControlOutcomeKind.ACTIVE_DRR_PROFILE,
                profile=settings.shop_profile,
                tier=DrrResolutionTier.SHOP,
            )

        return EffectiveControlSuccess(
            kind=EffectiveControlOutcomeKind.LEGACY_TIER,
        )
