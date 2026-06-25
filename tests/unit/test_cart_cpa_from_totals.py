"""Unit-тесты CPC для UI Auto Shelf."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    cpc_from_totals,
)

pytestmark = pytest.mark.unit


def test_cpc_from_totals_zero_clicks_returns_inf() -> None:
    assert cpc_from_totals(421.23, 0) == float("inf")


def test_cpc_from_totals_with_clicks() -> None:
    assert cpc_from_totals(100.0, 5) == pytest.approx(20.0)
