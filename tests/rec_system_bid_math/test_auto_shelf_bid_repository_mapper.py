"""Unit-тест mapper'а CH rows в bucket observations."""

from __future__ import annotations

from datetime import datetime

from app.domain.rec_system_bid_math.hour_observation_builder import (
    build_hour_observations_from_buckets,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    build_bid_bucket_observations_from_ch_rows,
)


def test_build_bid_bucket_observations_from_ch_rows() -> None:
    rows = [
        {
            "bid_minor": 100,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "delta_impressions": 10,
        },
        {
            "bid_minor": 100,
            "bucket_start": datetime(2026, 6, 7, 3, 15),
            "delta_impressions": 20,
        },
        {
            "bid_minor": 100,
            "bucket_start": datetime(2026, 6, 7, 3, 30),
            "delta_impressions": 30,
        },
        {
            "bid_minor": 100,
            "bucket_start": datetime(2026, 6, 7, 3, 45),
            "delta_impressions": 40,
        },
    ]

    buckets = build_bid_bucket_observations_from_ch_rows(rows)
    result = build_hour_observations_from_buckets(buckets)

    assert len(buckets) == 4
    assert len(result) == 1
    assert result[0].bid == 100
    assert result[0].hour == 3
    assert result[0].impressions_sum == 100.0

