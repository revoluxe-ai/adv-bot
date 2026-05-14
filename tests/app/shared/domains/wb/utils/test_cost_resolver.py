"""Tests for cost resolver utility."""

import pytest
from unittest.mock import Mock

from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost,
    resolve_target_cost_from_context,
    resolve_target_cost_from_summary,
    resolve_target_cost_threshold_kind,
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
        """When plan is fulfilled, should return current target."""
        summary = Mock()
        summary.fact_predict_orders = 100  # plan fulfilled

        result = resolve_target_cost_from_summary(
            summary,
            plan_orders=100,
            plan_target_pay_for_order=500.0,
            plan_max_pay_for_order=800.0,
        )

        assert result == 500.0

    def test_returns_max_when_plan_not_fulfilled(self):
        """When plan is not fulfilled, should return current max."""
        summary = Mock()
        summary.fact_predict_orders = 50  # plan not fulfilled

        result = resolve_target_cost_from_summary(
            summary,
            plan_orders=100,
            plan_target_pay_for_order=500.0,
            plan_max_pay_for_order=800.0,
        )

        assert result == 800.0

    def test_returns_target_when_plan_exceeded(self):
        """When plan is exceeded, should return current target."""
        summary = Mock()
        summary.fact_predict_orders = 150  # plan exceeded

        result = resolve_target_cost_from_summary(
            summary,
            plan_orders=100,
            plan_target_pay_for_order=500.0,
            plan_max_pay_for_order=800.0,
        )

        assert result == 500.0

    def test_returns_none_when_summary_is_none(self):
        """When summary is None, should return None."""
        result = resolve_target_cost_from_summary(
            None,
            plan_orders=100,
            plan_target_pay_for_order=500.0,
            plan_max_pay_for_order=800.0,
        )

        assert result is None

    def test_returns_none_when_current_plan_orders_is_none(self):
        """When current plan_orders is None, should return None."""
        summary = Mock()
        summary.fact_predict_orders = 100

        result = resolve_target_cost_from_summary(
            summary,
            plan_orders=None,
            plan_target_pay_for_order=500.0,
            plan_max_pay_for_order=800.0,
        )

        assert result is None

    def test_returns_none_when_current_target_is_none(self):
        """When current plan_target_pay_for_order is None, should return None."""
        summary = Mock()
        summary.fact_predict_orders = 100

        result = resolve_target_cost_from_summary(
            summary,
            plan_orders=100,
            plan_target_pay_for_order=None,
            plan_max_pay_for_order=800.0,
        )

        assert result is None

    def test_returns_none_when_current_max_is_none(self):
        """When current plan_max_pay_for_order is None, should return None."""
        summary = Mock()
        summary.fact_predict_orders = 50

        result = resolve_target_cost_from_summary(
            summary,
            plan_orders=100,
            plan_target_pay_for_order=500.0,
            plan_max_pay_for_order=None,
        )

        assert result is None

    def test_treats_none_fact_orders_as_zero(self):
        """When fact_predict_orders is None, should treat as 0."""
        summary = Mock()
        summary.fact_predict_orders = None  # treated as 0

        result = resolve_target_cost_from_summary(
            summary,
            plan_orders=100,
            plan_target_pay_for_order=500.0,
            plan_max_pay_for_order=800.0,
        )

        # 0 < 100, so should return max
        assert result == 800.0


class TestResolveTargetCost:
    """Tests for resolve_target_cost (scalar arguments)."""

    def test_returns_target_when_plan_fulfilled(self):
        """When plan is fulfilled, should return plan_target_pay_for_order."""
        result = resolve_target_cost(100, 500.0, 800.0, 100.0)
        assert result == 500.0

    def test_returns_max_when_plan_not_fulfilled(self):
        """When plan is not fulfilled, should return plan_max_pay_for_order."""
        result = resolve_target_cost(100, 500.0, 800.0, 50.0)
        assert result == 800.0

    def test_returns_target_when_plan_exceeded(self):
        """When plan is exceeded, should return plan_target_pay_for_order."""
        result = resolve_target_cost(100, 500.0, 800.0, 150.0)
        assert result == 500.0

    def test_returns_none_when_plan_orders_is_none(self):
        result = resolve_target_cost(None, 500.0, 800.0, 100.0)
        assert result is None

    def test_returns_none_when_plan_target_is_none(self):
        result = resolve_target_cost(100, None, 800.0, 100.0)
        assert result is None

    def test_returns_none_when_plan_max_is_none(self):
        result = resolve_target_cost(100, 500.0, None, 50.0)
        assert result is None

    def test_treats_none_fact_orders_as_zero(self):
        """When fact_predict_orders is None, should treat as 0."""
        result = resolve_target_cost(100, 500.0, 800.0, None)
        assert result == 800.0

    def test_boundary_fact_equals_plan_returns_target(self):
        """When fact_predict_orders == plan_orders, should return target."""
        result = resolve_target_cost(10, 100, 200, 10.0)
        assert result == 100.0

    def test_int_plan_values_returned_as_float(self):
        """Result should be float for int plan values."""
        result = resolve_target_cost(100, 500, 800, 100.0)
        assert result == 500.0
        assert isinstance(result, float)


class TestResolveTargetCostThresholdKind:
    """resolve_target_cost_threshold_kind stays aligned with resolve_target_cost."""

    def test_returns_target_when_plan_fulfilled(self) -> None:
        assert resolve_target_cost_threshold_kind(100, 500.0, 800.0, 100.0) == "target"

    def test_returns_max_when_plan_not_fulfilled(self) -> None:
        assert resolve_target_cost_threshold_kind(100, 500.0, 800.0, 50.0) == "max"

    def test_returns_none_when_resolve_returns_none(self) -> None:
        assert resolve_target_cost_threshold_kind(None, 500.0, 800.0, 100.0) is None

    def test_none_fact_same_as_resolve_uses_zero_branch(self) -> None:
        assert resolve_target_cost_threshold_kind(100, 500.0, 800.0, None) == "max"
