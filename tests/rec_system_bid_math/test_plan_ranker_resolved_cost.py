"""Тесты выбора resolved_order_cost в plan_ranker."""

from app.domain.rec_system_bid_math.plan_ranker import (
    PlanContext,
    rank_bids_for_sales_plan,
)


def test_resolved_order_cost_uses_max_order_cost_when_forecast_below_plan() -> None:
    """Если projected sales ниже плана, resolved cost должен быть max_order_cost."""
    bid_model_result = {
        "expected_ranked": [
            {
                "bid": 100,
                "expected_daily_impressions": 10_000.0,
                "confidence": 0.9,
                "uncertainty": 1000.0,
                "main_score": 9_500.0,
                "test_score": 10_750.0,
                "own_anchor": 0.5,
            }
        ]
    }
    context = PlanContext(
        sales_plan=200.0,
        current_fact_sales=100.0,
        current_sales_forecast=90.0,
        target_order_cost=150.0,
        max_order_cost=250.0,
        click_to_order_cr_7d=0.05,
    )

    ranked = rank_bids_for_sales_plan(bid_model_result, context, {100: 0.01})

    assert ranked[0]["resolved_order_cost_minor"] == 25_000.0
    assert ranked[0]["resolved_order_cost_rub"] == 250.0


def test_resolved_order_cost_uses_target_order_cost_when_forecast_meets_plan() -> None:
    """Если projected sales не ниже плана, resolved cost должен быть target_order_cost."""
    bid_model_result = {
        "expected_ranked": [
            {
                "bid": 100,
                "expected_daily_impressions": 10_000.0,
                "confidence": 0.9,
                "uncertainty": 1000.0,
                "main_score": 9_500.0,
                "test_score": 10_750.0,
                "own_anchor": 0.5,
            }
        ]
    }
    context = PlanContext(
        sales_plan=100.0,
        current_fact_sales=100.0,
        current_sales_forecast=110.0,
        target_order_cost=150.0,
        max_order_cost=250.0,
        click_to_order_cr_7d=0.05,
    )

    ranked = rank_bids_for_sales_plan(bid_model_result, context, {100: 0.01})

    assert ranked[0]["resolved_order_cost_minor"] == 15_000.0
    assert ranked[0]["resolved_order_cost_rub"] == 150.0


def test_zero_ctr_keeps_bid_and_forces_infinite_plan_costs() -> None:
    """Нулевой CTR не должен выкидывать ставку из plan_ranked."""
    bid_model_result = {
        "expected_ranked": [
            {
                "bid": 100,
                "expected_daily_impressions": 10_000.0,
                "confidence": 0.9,
                "uncertainty": 1000.0,
                "main_score": 9_500.0,
                "test_score": 10_750.0,
                "own_anchor": 0.5,
            }
        ]
    }
    context = PlanContext(
        sales_plan=105.0,
        current_fact_sales=100.0,
        current_sales_forecast=104.0,
        target_order_cost=150.0,
        max_order_cost=250.0,
        click_to_order_cr_7d=0.05,
    )

    ranked = rank_bids_for_sales_plan(bid_model_result, context, {100: 0.0})

    assert ranked[0]["bid"] == 100
    assert ranked[0]["expected_clicks"] == 0
    assert ranked[0]["expected_orders"] == 0
    assert ranked[0]["expected_order_cost_minor"] == float("inf")
    assert ranked[0]["expected_order_cost_rub"] == float("inf")
    assert ranked[0]["order_cost_overlimit_minor"] == float("inf")
    assert ranked[0]["plan_distance_score"] == float("inf")
