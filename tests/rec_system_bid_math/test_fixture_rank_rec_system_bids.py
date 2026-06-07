"""Fixture-based read-only test for rec_system bid ranking."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
    build_hour_observations_from_buckets,
)
from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.domain.rec_system_bid_math.service import rank_rec_system_bids


def test_fixture_rank_rec_system_bids() -> None:
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
    distinct_hour_bids = {obs.bid for obs in hours}
    distinct_hours = {obs.hour for obs in hours}
    ctr_by_bid = {bid: 0.02 for bid in distinct_hour_bids}
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

    assert len(payload) > 0
    assert len(buckets) > 0
    assert len(hours) > 0
    assert len(distinct_hour_bids) >= 2
    assert len(distinct_hours) >= 2
    assert all(obs.valid_hours_count == 1 for obs in hours)

    bid_result = result["bid_result"]
    plan_ranked = result["plan_ranked"]
    expected_ranked = bid_result["expected_ranked"]

    assert expected_ranked
    assert plan_ranked
    assert len(plan_ranked) == len(expected_ranked)
    assert {row["bid"] for row in plan_ranked} == {row["bid"] for row in expected_ranked}
    assert all(not math.isnan(row["plan_score"]) for row in plan_ranked)
