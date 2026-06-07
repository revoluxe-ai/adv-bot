"""Проверка связки run_bid_model и планового ранжировщика."""

from app.domain.rec_system_bid_math.bid_model import run_bid_model
from app.domain.rec_system_bid_math.plan_ranker import (
    PlanContext,
    rank_bids_for_sales_plan,
)
from tests.rec_system_bid_math.synthetic_cases import (
    make_one_night_hour_candidate_obs,
)


def test_bid_model_result_can_be_ranked_by_sales_plan() -> None:
    """Плановый ранжировщик должен работать поверх результата bid-модели."""
    obs, _truth = make_one_night_hour_candidate_obs()
    result = run_bid_model(obs)

    context = PlanContext(
        sales_plan=3000.0,
        current_fact_sales=0.0,
        current_sales_forecast=2500.0,
        target_order_cost=150.0,
        max_order_cost=250.0,
        click_to_order_cr_7d=0.05,
    )
    ctr_by_bid = {row["bid"]: 0.01 for row in result["expected_ranked"]}
    plan_ranked = rank_bids_for_sales_plan(result, context, ctr_by_bid)

    assert len(plan_ranked) == len(result["expected_ranked"])
    assert result["expected_ranked"][0]["bid"] == 160
    assert plan_ranked[0]["bid"] != 160

    for row in plan_ranked:
        assert "expected_orders" in row
        assert "expected_order_cost" in row
        assert "sales_dist" in row
        assert "plan_score" in row
