"""Unit tests for shared CH row -> bucket observation mapper."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
    build_hour_observations_from_buckets,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.bid_bucket_row_mapper import (
    build_bid_bucket_observations_from_ch_rows,
)

BucketingBuilder = Callable[[list[dict[str, object]]], list[BidBucketObservation]]


@pytest.mark.parametrize("builder", [build_bid_bucket_observations_from_ch_rows])
def test_build_bid_bucket_observations_from_ch_rows_groups_same_bucket_rows(
    builder: BucketingBuilder,
) -> None:
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

    buckets = builder(rows)
    result = build_hour_observations_from_buckets(buckets)

    assert len(buckets) == 4
    assert len(result) == 1
    assert result[0].bid == 100
    assert result[0].hour == 3
    assert result[0].impressions_sum == 100.0


@pytest.mark.parametrize("builder", [build_bid_bucket_observations_from_ch_rows])
def test_build_bid_bucket_observations_from_ch_rows_keeps_same_bucket_different_bids(
    builder: BucketingBuilder,
) -> None:
    rows = [
        {
            "bid_minor": 100,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "delta_impressions": 10,
        },
        {
            "bid_minor": 101,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "delta_impressions": 20,
        },
    ]

    buckets = builder(rows)

    assert len(buckets) == 2
    assert {bucket.bid for bucket in buckets} == {100, 101}
    assert all(bucket.bucket_start == datetime(2026, 6, 7, 3, 0) for bucket in buckets)


@pytest.mark.parametrize("builder", [build_bid_bucket_observations_from_ch_rows])
def test_build_bid_bucket_observations_from_ch_rows_keeps_same_bucket_different_prices(
    builder: BucketingBuilder,
) -> None:
    rows = [
        {
            "bid_minor": 100,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "delta_impressions": 10,
        },
        {
            "bid_minor": 100,
            "price_minor": 800,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "delta_impressions": 20,
        },
    ]

    buckets = builder(rows)

    assert len(buckets) == 2
    assert {bucket.price_minor for bucket in buckets} == {700, 800}
    assert all(bucket.bid == 100 for bucket in buckets)


@pytest.mark.parametrize("builder", [build_bid_bucket_observations_from_ch_rows])
def test_build_bid_bucket_observations_from_ch_rows_rejects_mixed_bid_hour(
    builder: BucketingBuilder,
) -> None:
    rows = [
        {
            "bid_minor": 100,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "delta_impressions": 10,
        },
        {
            "bid_minor": 100,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 15),
            "delta_impressions": 20,
        },
        {
            "bid_minor": 101,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 30),
            "delta_impressions": 30,
        },
        {
            "bid_minor": 101,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 45),
            "delta_impressions": 40,
        },
    ]

    buckets = builder(rows)
    result = build_hour_observations_from_buckets(buckets)

    assert len(buckets) == 4
    assert result == []


@pytest.mark.parametrize("builder", [build_bid_bucket_observations_from_ch_rows])
def test_build_bid_bucket_observations_from_ch_rows_rejects_mixed_price_hour(
    builder: BucketingBuilder,
) -> None:
    rows = [
        {
            "bid_minor": 100,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "delta_impressions": 10,
        },
        {
            "bid_minor": 100,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 15),
            "delta_impressions": 20,
        },
        {
            "bid_minor": 100,
            "price_minor": 800,
            "bucket_start": datetime(2026, 6, 7, 3, 30),
            "delta_impressions": 30,
        },
        {
            "bid_minor": 100,
            "price_minor": 700,
            "bucket_start": datetime(2026, 6, 7, 3, 45),
            "delta_impressions": 40,
        },
    ]

    buckets = builder(rows)
    result = build_hour_observations_from_buckets(buckets)

    assert len(buckets) == 4
    assert result == []
