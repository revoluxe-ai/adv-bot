"""Unit-тесты read-only orchestration service."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    build_bid_bucket_observations_from_ch_rows,
)


def test_build_bid_bucket_observations_from_ch_rows_sums_rows_in_bucket() -> None:
    rows = [
        {
            "event_id": "a",
            "version": 1,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 10,
            "delta_clicks": 1,
            "delta_orders": 0,
            "delta_spend": 1.5,
        },
        {
            "event_id": "a",
            "version": 2,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 11,
            "delta_clicks": 2,
            "delta_orders": 0,
            "delta_spend": 1.7,
        },
    ]

    buckets = build_bid_bucket_observations_from_ch_rows(rows)

    assert len(buckets) == 1
    assert buckets[0].impressions == 21.0
    assert buckets[0].price_minor == 700


@pytest.mark.asyncio
async def test_debug_fetch_and_rank_rec_system_bids_for_nmid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FakeRepository:
        async def fetch_rec_bid_bucket_observations_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> list[object]:
            _ = (nmid, mode, date_from, date_to)
            return build_bid_bucket_observations_from_ch_rows(
                [
                    {
                        "event_id": "a1",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 0),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 10,
                        "delta_clicks": 1,
                        "delta_orders": 0,
                        "delta_spend": 1.5,
                    },
                    {
                        "event_id": "a2",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 15),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 20,
                        "delta_clicks": 2,
                        "delta_orders": 0,
                        "delta_spend": 2.5,
                    },
                    {
                        "event_id": "a3",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 30),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 30,
                        "delta_clicks": 3,
                        "delta_orders": 0,
                        "delta_spend": 3.5,
                    },
                    {
                        "event_id": "a4",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 45),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 40,
                        "delta_clicks": 4,
                        "delta_orders": 1,
                        "delta_spend": 4.5,
                    },
                ]
            )

        async def fetch_rec_bid_ctr_by_bid_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> dict[int, float]:
            _ = (nmid, mode, date_from, date_to)
            return {100: 0.2}

    service = AutoShelfBidRecommendationReadService(FakeRepository())
    with caplog.at_level("INFO"):
        result = await service.debug_fetch_and_rank_rec_system_bids_for_nmid(
            nmid=123,
            mode="main",
            date_from=datetime(2026, 6, 7, 0, 0),
            date_to=datetime(2026, 6, 8, 0, 0),
            plan_context=PlanContext(
                sales_plan=100.0,
                current_fact_sales=10.0,
                current_sales_forecast=90.0,
                target_order_cost=100.0,
                max_order_cost=120.0,
                click_to_order_cr_7d=0.1,
            ),
            ctr_by_bid={100: 0.2},
        )

    assert "diagnostics" in result
    assert "bid_result" in result
    assert "plan_ranked" in result
    assert any("auto_shelf_bid_debug diagnostics=" in message for message in caplog.messages)
    assert any("expected_ranked_top10" in message for message in caplog.messages)
    assert any("main_ranked_top10" in message for message in caplog.messages)
    assert any("test_ranked_top10" in message for message in caplog.messages)
    assert any("plan_ranked_top10" in message for message in caplog.messages)


@pytest.mark.asyncio
async def test_fetch_bid_hour_observation_diagnostics() -> None:
    class FakeRepository:
        async def fetch_rec_bid_bucket_observations_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> list[object]:
            _ = (nmid, mode, date_from, date_to)
            return build_bid_bucket_observations_from_ch_rows(
                [
                    {
                        "event_id": "a1",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 0),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 10,
                    },
                    {
                        "event_id": "a2",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 15),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 20,
                    },
                    {
                        "event_id": "a3",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 30),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 30,
                    },
                    {
                        "event_id": "a4",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 45),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 40,
                    },
                    {
                        "event_id": "b1",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 0),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 10,
                    },
                    {
                        "event_id": "b2",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 15),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 20,
                    },
                    {
                        "event_id": "b3",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 30),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 30,
                    },
                    {
                        "event_id": "b4",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 45),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 40,
                    },
                ]
            )

        async def fetch_rec_bid_ctr_by_bid_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> dict[int, float]:
            _ = (nmid, mode, date_from, date_to)
            return {100: 0.2}

    service = AutoShelfBidRecommendationReadService(FakeRepository())
    summary = await service.fetch_bid_hour_observation_diagnostics(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert summary["raw_rows_count"] == 8
    assert summary["valid_bucket_count"] == 8
    assert summary["valid_hour_count"] == 2
    assert summary["observations_count"] == 2
    assert summary["distinct_bids"] == 2
    assert summary["invalid_bucket_reason_counts"] == {}
    assert summary["invalid_hour_reason_counts"] == {}


@pytest.mark.asyncio
async def test_fetch_and_rank_rec_system_bids_for_nmid_returns_plan_ranked() -> None:
    class FakeRepository:
        async def fetch_rec_bid_bucket_observations_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> list[object]:
            _ = (nmid, mode, date_from, date_to)
            return build_bid_bucket_observations_from_ch_rows(
                [
                    {
                        "event_id": "a1",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 0),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 10,
                        "delta_clicks": 1,
                        "delta_orders": 0,
                        "delta_spend": 1.5,
                    },
                    {
                        "event_id": "a2",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 15),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 20,
                        "delta_clicks": 2,
                        "delta_orders": 0,
                        "delta_spend": 2.5,
                    },
                    {
                        "event_id": "a3",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 30),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 30,
                        "delta_clicks": 3,
                        "delta_orders": 0,
                        "delta_spend": 3.5,
                    },
                    {
                        "event_id": "a4",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 45),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 40,
                        "delta_clicks": 4,
                        "delta_orders": 1,
                        "delta_spend": 4.5,
                    },
                ]
            )

        async def fetch_rec_bid_ctr_by_bid_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> dict[int, float]:
            _ = (nmid, mode, date_from, date_to)
            return {100: 0.2}

    service = AutoShelfBidRecommendationReadService(FakeRepository())
    result = await service.fetch_and_rank_rec_system_bids_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        plan_context=PlanContext(
            sales_plan=100.0,
            current_fact_sales=10.0,
            current_sales_forecast=90.0,
            target_order_cost=100.0,
            max_order_cost=120.0,
            click_to_order_cr_7d=0.1,
        ),
        ctr_by_bid={100: 0.2},
    )

    assert "bid_result" in result
    assert "plan_ranked" in result
    assert result["plan_ranked"]


@pytest.mark.asyncio
async def test_fetch_and_rank_rec_system_bids_for_nmid_returns_empty_payload_on_no_hours() -> None:
    class FakeRepository:
        async def fetch_rec_bid_bucket_observations_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> list[object]:
            _ = (nmid, mode, date_from, date_to)
            return []

        async def fetch_rec_bid_ctr_by_bid_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> dict[int, float]:
            _ = (nmid, mode, date_from, date_to)
            return {}

    service = AutoShelfBidRecommendationReadService(FakeRepository())
    result = await service.fetch_and_rank_rec_system_bids_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        plan_context=PlanContext(
            sales_plan=100.0,
            current_fact_sales=10.0,
            current_sales_forecast=90.0,
            target_order_cost=100.0,
            max_order_cost=120.0,
            click_to_order_cr_7d=0.1,
        ),
        ctr_by_bid={100: 0.2},
    )

    assert result["plan_ranked"] == []
    assert result["best_plan_bid"] is None
    assert result["best_expected_bid"] is None
    assert result["diagnostics"]["hour_observation_count"] == 0
    assert result["view"]["plan_ranked"] == []


@pytest.mark.asyncio
async def test_fetch_and_rank_rec_system_bids_for_nmid_raises_on_missing_ctr() -> None:
    class FakeRepository:
        async def fetch_rec_bid_bucket_observations_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> list[object]:
            _ = (nmid, mode, date_from, date_to)
            return build_bid_bucket_observations_from_ch_rows(
                [
                    {
                        "event_id": "a1",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 0),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 10,
                    },
                    {
                        "event_id": "a2",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 15),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 20,
                    },
                    {
                        "event_id": "a3",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 30),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 30,
                    },
                    {
                        "event_id": "a4",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 45),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 40,
                    },
                    {
                        "event_id": "a5",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 0),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 10,
                    },
                    {
                        "event_id": "a6",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 15),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 20,
                    },
                    {
                        "event_id": "a7",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 30),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 30,
                    },
                    {
                        "event_id": "a8",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 4, 45),
                        "bid_minor": 200,
                        "price_minor": 700,
                        "delta_impressions": 40,
                    },
                ]
            )

        async def fetch_rec_bid_ctr_by_bid_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> dict[int, float]:
            _ = (nmid, mode, date_from, date_to)
            return {100: 0.2}

    service = AutoShelfBidRecommendationReadService(FakeRepository())

    with pytest.raises(ValueError, match=r"Missing CTR for bids: \[200\]"):
        await service.fetch_and_rank_rec_system_bids_for_nmid(
            nmid=123,
            mode="main",
            date_from=datetime(2026, 6, 7, 0, 0),
            date_to=datetime(2026, 6, 8, 0, 0),
            plan_context=PlanContext(
                sales_plan=100.0,
                current_fact_sales=10.0,
                current_sales_forecast=90.0,
                target_order_cost=100.0,
                max_order_cost=120.0,
                click_to_order_cr_7d=0.1,
            ),
            ctr_by_bid={100: 0.2},
        )


@pytest.mark.asyncio
async def test_get_rec_bid_recommendations_returns_full_payload() -> None:
    class FakeRepository:
        async def fetch_rec_bid_bucket_observations_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> list[object]:
            _ = (nmid, mode, date_from, date_to)
            return build_bid_bucket_observations_from_ch_rows(
                [
                    {
                        "event_id": "a1",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 0),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 10,
                    },
                    {
                        "event_id": "a2",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 15),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 20,
                    },
                    {
                        "event_id": "a3",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 30),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 30,
                    },
                    {
                        "event_id": "a4",
                        "version": 1,
                        "bucket_start": datetime(2026, 6, 7, 3, 45),
                        "bid_minor": 100,
                        "price_minor": 700,
                        "delta_impressions": 40,
                    },
                ]
            )

        async def fetch_rec_bid_ctr_by_bid_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> dict[int, float]:
            _ = (nmid, mode, date_from, date_to)
            return {100: 0.2}

    service = AutoShelfBidRecommendationReadService(FakeRepository())
    result = await service.get_rec_bid_recommendations(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        plan_context=PlanContext(
            sales_plan=100.0,
            current_fact_sales=10.0,
            current_sales_forecast=90.0,
            target_order_cost=100.0,
            max_order_cost=120.0,
            click_to_order_cr_7d=0.1,
        ),
        ctr_by_bid={100: 0.2},
    )

    assert result["bid_result"]["expected_ranked"]
    assert result["plan_ranked"]
    assert result["best_plan_bid"] == 100
    assert result["best_expected_bid"] == 100
    assert result["diagnostics"]["bucket_count"] == 4
    assert result["diagnostics"]["hour_observation_count"] == 1
    assert "view" in result
    assert {
        "diagnostics",
        "best_expected_bid",
        "best_plan_bid",
        "expected_ranked",
        "plan_ranked",
    } <= set(result["view"].keys())


@pytest.mark.asyncio
async def test_get_rec_bid_recommendations_returns_empty_payload_on_no_hours() -> None:
    class FakeRepository:
        async def fetch_rec_bid_bucket_observations_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
            ) -> list[object]:
            _ = (nmid, mode, date_from, date_to)
            return []

        async def fetch_rec_bid_ctr_by_bid_for_nmid(
            self,
            nmid: int,
            mode: str,
            date_from: datetime,
            date_to: datetime,
        ) -> dict[int, float]:
            _ = (nmid, mode, date_from, date_to)
            return {}

    service = AutoShelfBidRecommendationReadService(FakeRepository())
    result = await service.get_rec_bid_recommendations(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        plan_context=PlanContext(
            sales_plan=100.0,
            current_fact_sales=10.0,
            current_sales_forecast=90.0,
            target_order_cost=100.0,
            max_order_cost=120.0,
            click_to_order_cr_7d=0.1,
        ),
        ctr_by_bid={100: 0.2},
    )

    assert result["plan_ranked"] == []
    assert result["best_plan_bid"] is None
    assert result["best_expected_bid"] is None
    assert "view" in result
    assert result["view"]["plan_ranked"] == []
