"""Unit-тесты CPA с max(carts, 1)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    cart_cpa_from_totals,
)

pytestmark = pytest.mark.unit


def test_cart_cpa_from_totals_zero_carts_uses_one() -> None:
    assert cart_cpa_from_totals(421.23, 0) == pytest.approx(421.23)


def test_cart_cpa_from_totals_with_carts() -> None:
    assert cart_cpa_from_totals(100.0, 5) == pytest.approx(20.0)
