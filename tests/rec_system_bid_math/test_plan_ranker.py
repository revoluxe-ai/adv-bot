"""Тесты ранжирования ставок относительно плана продаж."""

from tests.rec_system_bid_math.plan_ranker import (
    PlanContext,
    rank_bids_for_sales_plan,
)


def test_bid_closer_to_sales_plan_ranks_above_higher_impressions_bid() -> None:
    """Ставка с меньшими показами должна победить при меньшем отклонении."""
    bid_model_result = {
        "expected_ranked": [
            {
                "bid": 200,
                "expected_daily_impressions": 20_000.0,
            },
            {
                "bid": 100,
                "expected_daily_impressions": 10_000.0,
            },
        ]
    }
    context = PlanContext(
        sales_plan=105.0,
        current_fact_sales=100.0,
        current_sales_forecast=104.0,
        target_order_cost=150.0,
        max_order_cost=250.0,
        ctr=0.01,
        click_to_order_cr_7d=0.05,
    )

    ranked = rank_bids_for_sales_plan(bid_model_result, context)

    assert [row["bid"] for row in ranked] == [100, 200]
    assert ranked[0]["projected_sales"] == context.sales_plan
    assert ranked[0]["plan_score"] < ranked[1]["plan_score"]
