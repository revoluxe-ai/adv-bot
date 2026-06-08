"""Unit-тесты read-only bucket query mapper."""

from __future__ import annotations

from datetime import datetime

from app.domain.rec_system_bid_math.hour_observation_builder import (
    build_hour_observations_from_buckets,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    build_bid_bucket_observations_from_ch_rows,
)


def test_build_bid_bucket_observations_from_ch_rows_sums_rows_in_one_bucket() -> None:
    rows = [
        {
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 10,
            "delta_clicks": 1,
            "delta_orders": 0,
            "delta_spend": 1.5,
        },
        {
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
    assert buckets[0].bid == 100
    assert buckets[0].price_minor == 700
    assert buckets[0].impressions == 21.0


def test_build_bid_bucket_observations_from_ch_rows_bid_conflict_keeps_both_rows() -> None:
    rows = [
        {
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 10,
        },
        {
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 120,
            "price_minor": 700,
            "delta_impressions": 11,
        },
    ]

    buckets = build_bid_bucket_observations_from_ch_rows(rows)

    assert len(buckets) == 2
    assert {(bucket.bid, bucket.price_minor, bucket.impressions) for bucket in buckets} == {
        (100, 700, 10.0),
        (120, 700, 11.0),
    }


def test_build_bid_bucket_observations_from_ch_rows_price_conflict_keeps_both_rows() -> None:
    rows = [
        {
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": None,
            "delta_impressions": 10,
        },
        {
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 11,
        },
    ]

    buckets = build_bid_bucket_observations_from_ch_rows(rows)

    assert len(buckets) == 2
    assert {(bucket.bid, bucket.price_minor, bucket.impressions) for bucket in buckets} == {
        (100, None, 10.0),
        (100, 700, 11.0),
    }


def test_build_bid_bucket_observations_from_ch_rows_to_hour_builder() -> None:
    rows = [
        {
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 10,
        },
        {
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 11,
        },
        {
            "bucket_start": datetime(2026, 6, 7, 3, 15),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 20,
        },
        {
            "bucket_start": datetime(2026, 6, 7, 3, 30),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 30,
        },
        {
            "bucket_start": datetime(2026, 6, 7, 3, 45),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 40,
        },
    ]

    buckets = build_bid_bucket_observations_from_ch_rows(rows)
    result = build_hour_observations_from_buckets(buckets)

    assert len(result) == 1
    assert result[0].bid == 100
    assert result[0].hour == 3
    assert result[0].impressions_sum == 111.0

