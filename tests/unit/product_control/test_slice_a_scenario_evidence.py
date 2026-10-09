"""
Slice-A scenario evidence (product-control-context plan S03, S07, S09, S16, S19–S22).

Pure domain only — no projector/adapter.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.product_control.application.ports.pricing import (
    EffectiveProductPrice,
    ProductPriceUnavailable,
)
from app.modules.product_control.application.ports.sales_economics import (
    ProductSalesEconomicsSnapshot,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.product_control.domain.effective_control_resolver import (
    EffectiveControlInput,
    EffectiveControlResolver,
)
from app.modules.product_control.domain.enums import (
    EffectiveControlOutcomeKind,
    ProductControlMode,
    ShopControlEnrollment,
)
from app.modules.product_control.domain.models import (
    EffectiveControlBlocked,
    EffectiveControlSuccess,
    ProductCpoSuccess,
    ProductRef,
)
from app.modules.product_control.domain.multi_nm_policy import (
    resolve_control_product_for_complex,
)
from app.modules.product_control.domain.product_cpo_resolver import ProductCpoResolver

pytestmark = pytest.mark.unit


def test_s03_single_nm_safe_resolve() -> None:
    res = resolve_control_product_for_complex("S", [14824677])
    assert res.product == ProductRef("S", 14824677)


def test_s07_inherit_shop_uses_shop_drr() -> None:
    shop_p = drr_profile_from_percent(12, 18)
    out = EffectiveControlResolver.resolve(
        EffectiveControlInput(
            shop_enrollment=ShopControlEnrollment.ENROLLED,
            product_mode=ProductControlMode.INHERIT_SHOP,
            shop_profile=shop_p,
            product_profile=None,
        )
    )
    assert isinstance(out, EffectiveControlSuccess)
    assert out.profile == shop_p


def test_s09_enrolled_no_profiles_legacy_tier() -> None:
    out = EffectiveControlResolver.resolve(
        EffectiveControlInput(
            shop_enrollment=ShopControlEnrollment.ENROLLED,
            product_mode=ProductControlMode.INHERIT_SHOP,
            shop_profile=None,
            product_profile=None,
        )
    )
    assert isinstance(out, EffectiveControlSuccess)
    assert out.kind == EffectiveControlOutcomeKind.LEGACY_TIER


def test_s16_pricing_port_types_separate_from_sales_economics() -> None:
    """Порты разделены типами; sales snapshot не является price."""
    price = EffectiveProductPrice(
        price_rub=Decimal("100.00"),
        observed_at=__import__("datetime").datetime(2026, 1, 1),
        source="test",
    )
    unavailable = ProductPriceUnavailable(reason="missing")
    economics = ProductSalesEconomicsSnapshot(
        period_start=__import__("datetime").date(2026, 1, 1),
        period_end=__import__("datetime").date(2026, 1, 7),
        orders_count=10,
        orders_sum_rub=Decimal("5000"),
    )
    assert price.price_rub != economics.orders_sum_rub
    assert isinstance(unavailable, ProductPriceUnavailable)


def test_s19_product_override_cannot_bypass_not_enrolled() -> None:
    out = EffectiveControlResolver.resolve(
        EffectiveControlInput(
            shop_enrollment=ShopControlEnrollment.NOT_ENROLLED,
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            shop_profile=None,
            product_profile=drr_profile_from_percent(5, 10),
        )
    )
    assert isinstance(out, EffectiveControlSuccess)
    assert out.kind == EffectiveControlOutcomeKind.LEGACY_NOT_ENROLLED


def test_s21_override_without_profile_invalid() -> None:
    out = EffectiveControlResolver.resolve(
        EffectiveControlInput(
            shop_enrollment=ShopControlEnrollment.ENROLLED,
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            shop_profile=drr_profile_from_percent(5, 10),
            product_profile=None,
        )
    )
    assert isinstance(out, EffectiveControlBlocked)
    assert out.kind == EffectiveControlOutcomeKind.INVALID_CONFIGURATION


def test_s22_domain_max_cpo_001_rub() -> None:
    profile = drr_profile_from_percent(10, 10)
    out = ProductCpoResolver.resolve(profile, Decimal("1234.56"))
    assert isinstance(out, ProductCpoSuccess)
    assert str(out.cpo.max_cpo_rub).count(".") == 1
    assert out.cpo.max_cpo_rub == Decimal("123.46")
