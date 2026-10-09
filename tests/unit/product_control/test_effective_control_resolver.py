"""Unit: EffectiveControlResolver — enrollment matrix и inheritance."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.product_control.domain.effective_control_resolver import (
    EffectiveControlInput,
    EffectiveControlResolver,
)
from app.modules.product_control.domain.enums import (
    DrrResolutionTier,
    EffectiveControlOutcomeKind,
    ProductControlBlockerReason,
    ProductControlMode,
    ShopControlEnrollment,
)
from app.modules.product_control.domain.models import EffectiveControlBlocked, EffectiveControlSuccess

pytestmark = pytest.mark.unit

_SHOP_P = drr_profile_from_percent(10, 15)
_SKU_P = drr_profile_from_percent(20, 25)


def _inp(**kwargs: object) -> EffectiveControlInput:
    defaults = {
        "shop_enrollment": ShopControlEnrollment.ENROLLED,
        "product_mode": ProductControlMode.INHERIT_SHOP,
        "shop_profile": None,
        "product_profile": None,
    }
    defaults.update(kwargs)
    return EffectiveControlInput(**defaults)  # type: ignore[arg-type]


def test_shop_not_enrolled_master_gate() -> None:
    result = EffectiveControlResolver.resolve(
        _inp(
            shop_enrollment=ShopControlEnrollment.NOT_ENROLLED,
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            product_profile=_SKU_P,
        )
    )
    assert isinstance(result, EffectiveControlSuccess)
    assert result.kind == EffectiveControlOutcomeKind.LEGACY_NOT_ENROLLED


def test_shop_blocked_master_gate() -> None:
    result = EffectiveControlResolver.resolve(
        _inp(
            shop_enrollment=ShopControlEnrollment.BLOCKED,
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            product_profile=_SKU_P,
        )
    )
    assert isinstance(result, EffectiveControlBlocked)
    assert result.reason == ProductControlBlockerReason.SHOP_CONTROL_BLOCKED


def test_inherit_shop_with_shop_profile() -> None:
    result = EffectiveControlResolver.resolve(_inp(shop_profile=_SHOP_P))
    assert isinstance(result, EffectiveControlSuccess)
    assert result.kind == EffectiveControlOutcomeKind.ACTIVE_DRR_PROFILE
    assert result.profile == _SHOP_P
    assert result.tier == DrrResolutionTier.SHOP


def test_inherit_shop_without_profiles_legacy_tier() -> None:
    result = EffectiveControlResolver.resolve(_inp())
    assert isinstance(result, EffectiveControlSuccess)
    assert result.kind == EffectiveControlOutcomeKind.LEGACY_TIER


def test_override_enabled_with_product_profile() -> None:
    result = EffectiveControlResolver.resolve(
        _inp(
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            shop_profile=_SHOP_P,
            product_profile=_SKU_P,
        )
    )
    assert isinstance(result, EffectiveControlSuccess)
    assert result.profile == _SKU_P
    assert result.tier == DrrResolutionTier.PRODUCT


def test_override_without_product_profile_fail_closed() -> None:
    result = EffectiveControlResolver.resolve(
        _inp(
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            shop_profile=_SHOP_P,
        )
    )
    assert isinstance(result, EffectiveControlBlocked)
    assert result.kind == EffectiveControlOutcomeKind.INVALID_CONFIGURATION


def test_product_blocked_mode() -> None:
    result = EffectiveControlResolver.resolve(
        _inp(product_mode=ProductControlMode.BLOCKED),
    )
    assert isinstance(result, EffectiveControlBlocked)
    assert result.reason == ProductControlBlockerReason.PRODUCT_CONTROL_BLOCKED


def test_no_partial_field_inheritance_documented_by_atomic_profiles() -> None:
    """Shop и product профили атомарны — резолвер не смешивает поля."""
    mixed_shop = drr_profile_from_percent(5, 30)
    sku = drr_profile_from_percent(20, 22)
    result = EffectiveControlResolver.resolve(
        _inp(
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            shop_profile=mixed_shop,
            product_profile=sku,
        )
    )
    assert isinstance(result, EffectiveControlSuccess)
    assert result.profile == sku
    assert result.profile.max_drr_percent == Decimal("22")
