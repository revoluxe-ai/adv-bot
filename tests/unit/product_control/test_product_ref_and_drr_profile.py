"""Unit: ProductRef identity и инварианты DrrProfile."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.product_control.domain.invariants_drr import DrrProfileInvariantError
from app.modules.product_control.domain.models import DrrProfile, ProductRef

pytestmark = pytest.mark.unit


def test_product_ref_equality_and_identity() -> None:
    a = ProductRef(shop_id="s1", nmid=100)
    b = ProductRef(shop_id="s1", nmid=100)
    c = ProductRef(shop_id="s2", nmid=100)
    assert a == b
    assert a != c
    assert hash(a) == hash(b)


def test_product_ref_rejects_empty_shop() -> None:
    with pytest.raises(ValueError, match="shop_id"):
        ProductRef(shop_id="", nmid=1)


def test_drr_profile_requires_max_gte_target_on_construction() -> None:
    with pytest.raises(DrrProfileInvariantError):
        DrrProfile(
            target_drr_percent=Decimal("15"),
            max_drr_percent=Decimal("10"),
        )


def test_drr_profile_negative_target_rejected() -> None:
    with pytest.raises(DrrProfileInvariantError):
        DrrProfile(
            target_drr_percent=Decimal("-1"),
            max_drr_percent=Decimal("5"),
        )


def test_drr_profile_complete_profile_ok() -> None:
    profile = drr_profile_from_percent(8, 12)
    assert profile.target_drr_percent == Decimal("8")
    assert profile.max_drr_percent == Decimal("12")
