"""Contract test for rec_system bid ranking result shape."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
    build_hour_observations_from_buckets,
)
from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.domain.rec_system_bid_math.service import rank_rec_system_bids


def test_result_contract_shape() -> None:
    fixture_path = Path("tests/fixtures/rec_system_bid_math/rec_bid_debug_sample.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    buckets = [
        BidBucketObservation(
            bid=int(row["bid"]),
            bucket_start=datetime.fromisoformat(row["bucket_start"]),
            impressions=float(row["impressions"]),
            price_minor=None if row["price_minor"] is None else int(row["price_minor"]),
        )
        for row in payload
    ]
    hours = build_hour_observations_from_buckets(buckets)
    ctr_by_bid = {obs.bid: 0.02 for obs in hours}
    result = rank_rec_system_bids(
        observations=hours,
        plan_context=PlanContext(
            sales_plan=100.0,
            current_fact_sales=10.0,
            current_sales_forecast=90.0,
            target_order_cost=100.0,
            max_order_cost=120.0,
            click_to_order_cr_7d=0.1,
        ),
        ctr_by_bid=ctr_by_bid,
    )

    bid_result = result["bid_result"]
    plan_ranked = result["plan_ranked"]

    assert {"rows", "expected_ranked", "main_ranked", "test_ranked", "debug", "y_obs", "c_obs", "y_final", "c_final"} <= set(
        bid_result.keys()
    )

    expected_row_keys = {
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
    assert plan_ranked
    assert expected_row_keys <= set(plan_ranked[0].keys())
