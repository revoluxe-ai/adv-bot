"""Unit-тесты build_rec_bid_plan_context для auto_shelf_bid_control."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.rec_bid_plan_context import (
    build_rec_bid_plan_context,
)


@pytest.mark.unit
def test_build_rec_bid_plan_context_uses_explicit_max_order_cost_when_plan_not_met() -> None:
    """max_order_cost (original_max_cpo) не должен подменяться max_price_for_order."""
    plan_context = build_rec_bid_plan_context(
        sales_plan=500.0,
        current_fact_sales=100.0,
        current_sales_forecast=100.0,
        target_price_for_order=100.0,
        max_price_for_order=120.0,
        max_order_cost=250.0,
        click_to_order_cr_7d=0.2,
    )

    assert plan_context.target_order_cost == 120.0
    assert plan_context.max_order_cost == 250.0


@pytest.mark.unit
def test_build_rec_bid_plan_context_keeps_target_cost_and_max_order_cost_separate_when_plan_met() -> None:
    """При выполненном плане target берётся из target_price, max_order_cost — из аргумента."""
    plan_context = build_rec_bid_plan_context(
        sales_plan=500.0,
        current_fact_sales=500.0,
        current_sales_forecast=500.0,
        target_price_for_order=100.0,
        max_price_for_order=120.0,
        max_order_cost=250.0,
        click_to_order_cr_7d=0.2,
    )

    assert plan_context.target_order_cost == 100.0
    assert plan_context.max_order_cost == 250.0


@pytest.mark.unit
def test_build_rec_bid_plan_context_falls_back_to_max_price_for_order_without_max_order_cost() -> None:
    """Без max_order_cost сохраняется прежнее поведение: потолок = max_price_for_order."""
    plan_context = build_rec_bid_plan_context(
        sales_plan=500.0,
        current_fact_sales=100.0,
        current_sales_forecast=100.0,
        target_price_for_order=100.0,
        max_price_for_order=120.0,
        click_to_order_cr_7d=0.2,
    )

    assert plan_context.target_order_cost == 120.0
    assert plan_context.max_order_cost == 120.0
