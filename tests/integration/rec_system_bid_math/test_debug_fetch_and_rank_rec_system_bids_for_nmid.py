"""Read-only integration test for rec system bid debug entrypoint."""

from __future__ import annotations

import os
from datetime import datetime

import pytest

from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    AutoShelfBidRepository,
)


def _parse_dt(name: str) -> datetime:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} is not set")
    return datetime.fromisoformat(value)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_debug_fetch_and_rank_rec_system_bids_for_nmid() -> None:
    nmid_value = os.environ.get("REC_BID_DEBUG_NMID")
    if not nmid_value:
        pytest.skip("REC_BID_DEBUG_NMID is not set")

    nmid = int(nmid_value)
    mode = os.environ.get("REC_BID_DEBUG_MODE", "main")
    date_from = _parse_dt("REC_BID_DEBUG_DATE_FROM")
    date_to = _parse_dt("REC_BID_DEBUG_DATE_TO")

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    service = AutoShelfBidRecommendationReadService(repository)

    diagnostics = await service.fetch_bid_hour_observation_diagnostics(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
    )

    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
    )
    ctr_by_bid = {bucket.bid: 0.02 for bucket in buckets}

    result = await service.debug_fetch_and_rank_rec_system_bids_for_nmid(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
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

    assert diagnostics["raw_rows_count"] >= 0
    assert diagnostics["distinct_bids"] >= 0
    assert "bid_result" in result
    assert "plan_ranked" in result
