"""Extra unit coverage for cost_resolver helpers used by AutoUpdater v2."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
)
from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost,
    resolve_target_cost_from_context,
    resolve_target_cost_from_summary,
)

pytestmark = pytest.mark.unit


def test_resolve_target_cost_from_context_returns_max_when_plan_not_met() -> None:
    ctx = MagicMock()
    ctx.plan.orders = 10
    ctx.plan.target_pay_for_order = 100
    ctx.plan.max_pay_for_order = 300
    ctx.fact.predict_orders = 5.0
    assert resolve_target_cost_from_context(ctx) == 300


def test_resolve_target_cost_from_context_returns_target_when_plan_met() -> None:
    ctx = MagicMock()
    ctx.plan.orders = 10
    ctx.plan.target_pay_for_order = 100
    ctx.plan.max_pay_for_order = 300
    ctx.fact.predict_orders = 12.0
    assert resolve_target_cost_from_context(ctx) == 100


def test_resolve_target_cost_from_context_returns_none_when_missing_plan() -> None:
    ctx = MagicMock()
    ctx.plan = None
    ctx.fact = MagicMock()
    assert resolve_target_cost_from_context(ctx) is None


def test_resolve_target_cost_rejects_bool_plan_orders() -> None:
    assert resolve_target_cost(True, 100, 200, 5.0) is None


def test_resolve_target_cost_none_predict_treated_as_zero() -> None:
    assert resolve_target_cost(10, 50, 150, None) == 150


def test_resolve_target_cost_from_summary_none_summary() -> None:
    assert (
        resolve_target_cost_from_summary(
            None,
            plan_orders=10,
            plan_target_pay_for_order=50,
            plan_max_pay_for_order=150,
        )
        is None
    )


def test_resolve_target_cost_from_summary_uses_predict_orders() -> None:
    summary = PlanFactSummary(
        adv_id=1,
        fact_predict_orders=20.0,
        fact_pay_for_order=100.0,
    )
    assert (
        resolve_target_cost_from_summary(
            summary,
            plan_orders=10,
            plan_target_pay_for_order=40,
            plan_max_pay_for_order=90,
        )
        == 40
    )
