"""Tests for additional cost per order utility."""

import pytest

from app.shared.domains.wb.utils.additional_cost_per_order import (
    compute_additional_cost_per_order,
)


class TestComputeAdditionalCostPerOrder:
    """Tests for compute_additional_cost_per_order."""

    def test_addition_spend_and_orders_positive(self):
        """When addition spend and orders are positive, returns spend/orders."""
        # auto 1000 spend, 20 orders; keywords 200 spend, 5 orders → addition 800, 15+1=16
        assert compute_additional_cost_per_order(1000.0, 20, 200.0, 5) == 50.0  # 800/16

    def test_no_keyword_spend_or_orders(self):
        """When keyword spend/orders are 0, addition = full auto."""
        assert compute_additional_cost_per_order(500.0, 10, 0.0, 0) == 500.0 / 11  # +1 in denom

    def test_addition_spend_clamped_to_zero(self):
        """When keyword spend exceeds auto spend, addition_spend is 0."""
        # auto 100 spend, 5 orders; keywords 150 spend, 2 orders → addition_spend = 0, orders = 3+1=4
        assert compute_additional_cost_per_order(100.0, 5, 150.0, 2) == 0.0

    def test_addition_orders_clamped_then_plus_one(self):
        """When keyword orders >= auto orders, addition_orders = 0 + 1 = 1."""
        assert compute_additional_cost_per_order(100.0, 5, 10.0, 5) == 90.0 / 1  # 90.0
        assert compute_additional_cost_per_order(100.0, 5, 10.0, 10) == 90.0 / 1  # 90.0

    def test_zero_auto_orders(self):
        """When auto orders is 0, denominator is still 1 (no division by zero)."""
        assert compute_additional_cost_per_order(50.0, 0, 0.0, 0) == 50.0 / 1  # 50.0
