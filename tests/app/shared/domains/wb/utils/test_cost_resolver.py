"""Tests for cost resolver utility."""

import pytest
from unittest.mock import Mock

from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost_from_context,
    resolve_target_cost_from_summary,
)


class TestResolveTargetCostFromContext:
    """Tests for resolve_target_cost_from_context."""

    def test_returns_target_when_plan_fulfilled(self):
        """When plan is fulfilled, should return target_pay_for_order."""
        ctx = Mock()
        ctx.plan.orders = 100
        ctx.plan.target_pay_for_order = 500.0
        ctx.plan.max_pay_for_order = 800.0
        ctx.fact.predict_orders = 100  # plan fulfilled

        result = resolve_target_cost_from_context(ctx)

        assert result == 500.0

    def test_returns_max_when_plan_not_fulfilled(self):
        """When plan is not fulfilled, should return max_pay_for_order."""
        ctx = Mock()
        ctx.plan.orders = 100
        ctx.plan.target_pay_for_order = 500.0
        ctx.plan.max_pay_for_order = 800.0
        ctx.fact.predict_orders = 50  # plan not fulfilled

        result = resolve_target_cost_from_context(ctx)

        assert result == 800.0

    def test_returns_target_when_plan_exceeded(self):
        """When plan is exceeded, should return target_pay_for_order."""
        ctx = Mock()
        ctx.plan.orders = 100
        ctx.plan.target_pay_for_order = 500.0
        ctx.plan.max_pay_for_order = 800.0
        ctx.fact.predict_orders = 150  # plan exceeded

        result = resolve_target_cost_from_context(ctx)

        assert result == 500.0

    def test_returns_none_when_plan_is_none(self):
        """When plan is None, should return None."""
        ctx = Mock()
        ctx.plan = None
        ctx.fact = Mock()

        result = resolve_target_cost_from_context(ctx)

        assert result is None

    def test_returns_none_when_fact_is_none(self):
        """When fact is None, should return None."""
        ctx = Mock()
        ctx.plan = Mock()
        ctx.fact = None

        result = resolve_target_cost_from_context(ctx)

        assert result is None

    def test_returns_none_when_target_pay_for_order_is_none(self):
        """When target_pay_for_order is None, should return None."""
        ctx = Mock()
        ctx.plan.orders = 100
        ctx.plan.target_pay_for_order = None
        ctx.plan.max_pay_for_order = 800.0
        ctx.fact.predict_orders = 100

        result = resolve_target_cost_from_context(ctx)

        assert result is None

    def test_returns_none_when_max_pay_for_order_is_none(self):
        """When max_pay_for_order is None, should return None."""
        ctx = Mock()
        ctx.plan.orders = 100
        ctx.plan.target_pay_for_order = 500.0
        ctx.plan.max_pay_for_order = None
        ctx.fact.predict_orders = 50

        result = resolve_target_cost_from_context(ctx)

        assert result is None

    def test_returns_none_when_orders_is_none(self):
        """When plan orders is None, should return None."""
        ctx = Mock()
        ctx.plan.orders = None
        ctx.plan.target_pay_for_order = 500.0
        ctx.plan.max_pay_for_order = 800.0
        ctx.fact.predict_orders = 100

        result = resolve_target_cost_from_context(ctx)

        assert result is None

    def test_handles_attribute_error(self):
        """When accessing attributes raises AttributeError, should return None."""
        ctx = Mock()
        del ctx.plan

        result = resolve_target_cost_from_context(ctx)

        assert result is None

    def test_handles_type_error(self):
        """When comparison raises TypeError, should return None."""
        ctx = Mock()
        ctx.plan.orders = 100
        ctx.plan.target_pay_for_order = 500.0
        ctx.plan.max_pay_for_order = 800.0
        ctx.fact.predict_orders = "invalid"  # will cause TypeError

        result = resolve_target_cost_from_context(ctx)

        assert result is None


class TestResolveTargetCostFromSummary:
    """Tests for resolve_target_cost_from_summary."""

    def test_returns_target_when_plan_fulfilled(self):
        """When plan is fulfilled, should return plan_target_pay_for_order."""
        summary = Mock()
        summary.plan_orders = 100
        summary.plan_target_pay_for_order = 500.0
        summary.plan_max_pay_for_order = 800.0
        summary.fact_predict_orders = 100  # plan fulfilled

        result = resolve_target_cost_from_summary(summary)

        assert result == 500.0

    def test_returns_max_when_plan_not_fulfilled(self):
        """When plan is not fulfilled, should return plan_max_pay_for_order."""
        summary = Mock()
        summary.plan_orders = 100
        summary.plan_target_pay_for_order = 500.0
        summary.plan_max_pay_for_order = 800.0
        summary.fact_predict_orders = 50  # plan not fulfilled

        result = resolve_target_cost_from_summary(summary)

        assert result == 800.0

    def test_returns_target_when_plan_exceeded(self):
        """When plan is exceeded, should return plan_target_pay_for_order."""
        summary = Mock()
        summary.plan_orders = 100
        summary.plan_target_pay_for_order = 500.0
        summary.plan_max_pay_for_order = 800.0
        summary.fact_predict_orders = 150  # plan exceeded

        result = resolve_target_cost_from_summary(summary)

        assert result == 500.0

    def test_returns_none_when_summary_is_none(self):
        """When summary is None, should return None."""
        result = resolve_target_cost_from_summary(None)

        assert result is None

    def test_returns_none_when_plan_orders_is_none(self):
        """When plan_orders is None, should return None."""
        summary = Mock()
        summary.plan_orders = None
        summary.plan_target_pay_for_order = 500.0
        summary.plan_max_pay_for_order = 800.0
        summary.fact_predict_orders = 100

        result = resolve_target_cost_from_summary(summary)

        assert result is None

    def test_returns_none_when_plan_target_pay_for_order_is_none(self):
        """When plan_target_pay_for_order is None, should return None."""
        summary = Mock()
        summary.plan_orders = 100
        summary.plan_target_pay_for_order = None
        summary.plan_max_pay_for_order = 800.0
        summary.fact_predict_orders = 100

        result = resolve_target_cost_from_summary(summary)

        assert result is None

    def test_returns_none_when_plan_max_pay_for_order_is_none(self):
        """When plan_max_pay_for_order is None, should return None."""
        summary = Mock()
        summary.plan_orders = 100
        summary.plan_target_pay_for_order = 500.0
        summary.plan_max_pay_for_order = None
        summary.fact_predict_orders = 50

        result = resolve_target_cost_from_summary(summary)

        assert result is None

    def test_treats_none_fact_orders_as_zero(self):
        """When fact_predict_orders is None, should treat as 0."""
        summary = Mock()
        summary.plan_orders = 100
        summary.plan_target_pay_for_order = 500.0
        summary.plan_max_pay_for_order = 800.0
        summary.fact_predict_orders = None  # treated as 0

        result = resolve_target_cost_from_summary(summary)

        # 0 < 100, so should return max
        assert result == 800.0
