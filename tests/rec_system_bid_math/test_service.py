"""Тесты оркестрационного слоя rec_system_bid_math."""

from app.domain.rec_system_bid_math.input_models import BidHourObservation
from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.domain.rec_system_bid_math.service import rank_rec_system_bids


def test_rank_rec_system_bids_returns_bid_and_plan_blocks() -> None:
    """Сервис должен возвращать оба результата без внешних зависимостей."""
    observations = [
        BidHourObservation(
            bid=160,
            hour=3,
            impressions_sum=2000.0,
            valid_hours_count=1,
        ),
        BidHourObservation(
            bid=120,
            hour=3,
            impressions_sum=1000.0,
            valid_hours_count=1,
        ),
    ]
    context = PlanContext(
        sales_plan=100.0,
        current_fact_sales=0.0,
        current_sales_forecast=0.0,
        target_order_cost=150.0,
        max_order_cost=250.0,
        click_to_order_cr_7d=0.05,
    )
    ctr_by_bid = {160: 0.02, 120: 0.01}

    result = rank_rec_system_bids(observations, context, ctr_by_bid)

    assert "bid_result" in result
    assert "plan_ranked" in result
    assert result["bid_result"]["expected_ranked"]
    assert result["plan_ranked"]
