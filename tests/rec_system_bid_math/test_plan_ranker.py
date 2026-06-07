"""Тесты ранжирования ставок относительно плана продаж."""

from app.domain.rec_system_bid_math.plan_ranker import (
    PlanContext,
    rank_bids_for_sales_plan,
)


def test_bid_closer_to_sales_plan_ranks_above_higher_impressions_bid() -> None:
    """Ставка с меньшим плановым отклонением должна победить."""
    bid_model_result = {
        "expected_ranked": [
            {
                "bid": 200,
                "expected_daily_impressions": 20_000.0,
                "confidence": 0.8,
                "uncertainty": 4000.0,
                "main_score": 18_000.0,
                "test_score": 22_000.0,
                "own_anchor": 0.3,
            },
            {
                "bid": 100,
                "expected_daily_impressions": 10_000.0,
                "confidence": 0.9,
                "uncertainty": 1000.0,
                "main_score": 9_500.0,
                "test_score": 10_750.0,
                "own_anchor": 0.5,
            },
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
    ctr_by_bid = {100: 0.01, 200: 0.01}

    ranked = rank_bids_for_sales_plan(bid_model_result, context, ctr_by_bid)

    assert [row["bid"] for row in ranked] == [100, 200]
    assert set(ranked[0]) == {
        "bid",
        "ctr",
        "expected_impressions",
        "expected_clicks",
        "expected_orders",
        "expected_cost",
        "expected_order_cost_minor",
        "expected_order_cost_rub",
        "resolved_order_cost_minor",
        "resolved_order_cost_rub",
        "projected_sales",
        "needed_sales",
        "sales_miss",
        "sales_dist",
        "cpo_over_minor",
        "cpo_over_rub",
        "cpo_dist",
        "plan_score",
        "confidence",
        "uncertainty",
        "main_score",
        "test_score",
        "own_anchor",
    }
    assert ranked[0]["projected_sales"] == 105.0
    assert ranked[0]["plan_score"] <= ranked[1]["plan_score"]


def test_zero_ctr_keeps_bid_but_forces_infinite_costs() -> None:
    """Нулевой CTR не должен выкидывать ставку из ранжирования."""
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
    assert ranked[0]["cpo_over_minor"] == float("inf")
    assert ranked[0]["plan_score"] == float("inf")


def test_missing_ctr_raises_key_error() -> None:
    """Отсутствующий CTR для ставки должен падать явной ошибкой."""
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

    try:
        rank_bids_for_sales_plan(bid_model_result, context, {})
    except KeyError:
        assert True
    else:
        raise AssertionError("expected KeyError for missing ctr_by_bid entry")
