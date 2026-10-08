"""Unit: ProductCpoResolver — Decimal 0.01 RUB ROUND_HALF_UP."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.product_control.domain.enums import ProductControlBlockerReason
from app.modules.product_control.domain.models import ProductCpoBlocked, ProductCpoSuccess
from app.modules.product_control.domain.product_cpo_resolver import ProductCpoResolver

pytestmark = pytest.mark.unit


def test_missing_effective_price_blocked() -> None:
    profile = drr_profile_from_percent(10, 15)
    result = ProductCpoResolver.resolve(profile, None)
    assert isinstance(result, ProductCpoBlocked)
    assert result.reason == ProductControlBlockerReason.BLOCKED_BY_PRODUCT_PRICE_SOURCE


def test_cpo_rounding_half_up() -> None:
    profile = drr_profile_from_percent(10, 15)
    price = Decimal("999.99")
    result = ProductCpoResolver.resolve(profile, price)
    assert isinstance(result, ProductCpoSuccess)
    assert result.cpo.target_cpo_rub == Decimal("100.00")
    assert result.cpo.max_cpo_rub == Decimal("150.00")


def test_cpo_target_and_max_separate_rounding() -> None:
    profile = drr_profile_from_percent("7.5", "7.5")
    price = Decimal("33.33")
    result = ProductCpoResolver.resolve(profile, price)
    assert isinstance(result, ProductCpoSuccess)
    assert result.cpo.target_cpo_rub == Decimal("2.50")
    assert result.cpo.max_cpo_rub == Decimal("2.50")
