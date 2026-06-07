"""Validation tests for plan ranker input context."""

from __future__ import annotations

import pytest

from app.domain.rec_system_bid_math.plan_ranker import PlanContext


@pytest.mark.unit
@pytest.mark.parametrize("value", [-0.01, 1.01, 30.0])
def test_plan_context_rejects_non_fraction_click_to_order_cr(value: float) -> None:
    with pytest.raises(ValueError, match="click_to_order_cr_7d must be a fraction"):
        PlanContext(
            sales_plan=100.0,
            current_fact_sales=10.0,
            current_sales_forecast=90.0,
            target_order_cost=100.0,
            max_order_cost=120.0,
            click_to_order_cr_7d=value,
        )
