"""Tests for minor-unit handling in rec bid plan ranking."""

from __future__ import annotations

from app.domain.rec_system_bid_math.plan_ranker import (
    PlanContext,
    rank_bids_for_sales_plan,
)


def test_plan_ranker_uses_minor_units_for_cpo() -> None:
    """35000 should win when CPO is compared in minor units, not rubles."""
    bid_model_result = {
        "expected_ranked": [
            {
                "bid": 12000,
                "expected_daily_impressions": 30182.816662926038,
                "confidence": 0.9,
                "uncertainty": 2904.1655935441863,
                "main_score": 28730.733866153943,
                "test_score": 32360.940858084177,
                "own_anchor": 0.3713369372715348,
            },
            {
                "bid": 35000,
                "expected_daily_impressions": 115847.18246532125,
                "confidence": 0.2,
                "uncertainty": 92735.1157094873,
                "main_score": 69479.6246105776,
                "test_score": 185398.51924743672,
                "own_anchor": 0.003787878787878788,
            },
        ]
    }
    context = PlanContext(
        sales_plan=390.0,
        current_fact_sales=50.0,
        current_sales_forecast=0.0,
        target_order_cost=140.0,
        max_order_cost=590.0,
        click_to_order_cr_7d=0.034,
    )
    ctr_by_bid = {
        12000: 0.024783974300925108,
        35000: 0.017543859649122806,
    }

    ranked = rank_bids_for_sales_plan(bid_model_result, context, ctr_by_bid)

    assert ranked[0]["bid"] == 35000
    assert ranked[0]["resolved_order_cost_minor"] == 59000.0
    assert ranked[0]["resolved_order_cost_rub"] == 590.0
    assert ranked[0]["expected_order_cost_minor"] > 0
    assert ranked[0]["plan_distance_score"] < ranked[1]["plan_distance_score"]
