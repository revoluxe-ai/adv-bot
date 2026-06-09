"""Оркестрация чистой bid-math цепочки без внешних зависимостей."""

from typing import Any

from app.domain.rec_system_bid_math.bid_model import run_bid_model
from app.domain.rec_system_bid_math.input_models import (
    BidHourObservation,
    to_bid_model_obs,
)
from app.domain.rec_system_bid_math.plan_ranker import (
    PlanContext,
    rank_bids_for_sales_plan,
)


def rank_rec_system_bids(
    observations: list[BidHourObservation],
    plan_context: PlanContext,
    ctr_by_bid: dict[int, float],
) -> dict[str, Any]:
    """Построить bid_result и plan_ranked на основе внешних наблюдений."""
    obs = to_bid_model_obs(observations)
    bid_result = run_bid_model(obs)
    plan_ranked = rank_bids_for_sales_plan(
        bid_result,
        plan_context,
        ctr_by_bid=ctr_by_bid,
    )
    return {
        "bid_result": bid_result,
        "plan_ranked": plan_ranked,
    }
