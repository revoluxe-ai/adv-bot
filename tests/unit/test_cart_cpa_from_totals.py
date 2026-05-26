"""Unit-тесты CPC с max(clicks, 1)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    cpc_from_totals,
)

pytestmark = pytest.mark.unit


def test_cpc_from_totals_zero_clicks_uses_one() -> None:
    assert cpc_from_totals(421.23, 0) == pytest.approx(421.23)


def test_cpc_from_totals_with_clicks() -> None:
    assert cpc_from_totals(100.0, 5) == pytest.approx(20.0)
