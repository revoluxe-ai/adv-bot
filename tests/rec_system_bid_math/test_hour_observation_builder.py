"""Unit-тесты для hour-observation builder."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
    build_hour_observations_from_buckets,
)


def _make_four_bucket_hour(price_minor: int | None) -> list[BidBucketObservation]:
    return [
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 3, 0),
            impressions=10.0,
            price_minor=price_minor,
        ),
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 3, 15),
            impressions=20.0,
            price_minor=price_minor,
        ),
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 3, 30),
            impressions=30.0,
            price_minor=price_minor,
        ),
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 3, 45),
            impressions=40.0,
            price_minor=price_minor,
        ),
    ]


def test_build_hour_observations_from_buckets_all_none_price_is_valid() -> None:
    result = build_hour_observations_from_buckets(_make_four_bucket_hour(None))

    assert len(result) == 1
    assert result[0].bid == 100
    assert result[0].hour == 3
    assert result[0].impressions_sum == 100.0


def test_build_hour_observations_from_buckets_same_price_is_valid() -> None:
    result = build_hour_observations_from_buckets(_make_four_bucket_hour(700))

    assert len(result) == 1
    assert result[0].bid == 100
    assert result[0].hour == 3
    assert result[0].impressions_sum == 100.0


def test_build_hour_observations_from_buckets_mixed_none_price_is_invalid() -> None:
    buckets = _make_four_bucket_hour(None)
    buckets[0] = BidBucketObservation(
        bid=100,
        bucket_start=datetime(2026, 6, 7, 3, 0),
        impressions=10.0,
        price_minor=700,
    )

    result = build_hour_observations_from_buckets(buckets)

    assert result == []


def test_build_hour_observations_from_buckets_two_prices_is_invalid() -> None:
    buckets = _make_four_bucket_hour(700)
    buckets[2] = BidBucketObservation(
        bid=100,
        bucket_start=datetime(2026, 6, 7, 3, 30),
        impressions=30.0,
        price_minor=800,
    )

    result = build_hour_observations_from_buckets(buckets)

    assert result == []


def test_build_hour_observations_from_buckets_mixed_bid_is_invalid() -> None:
    buckets = _make_four_bucket_hour(700)
    buckets[2] = BidBucketObservation(
        bid=101,
        bucket_start=datetime(2026, 6, 7, 3, 30),
        impressions=30.0,
        price_minor=700,
    )

    result = build_hour_observations_from_buckets(buckets)

    assert result == []


def test_build_hour_observations_from_buckets_skips_three_buckets() -> None:
    buckets = _make_four_bucket_hour(700)[:3]

    result = build_hour_observations_from_buckets(buckets)

    assert result == []


def test_build_hour_observations_from_buckets_skips_grid_gap() -> None:
    buckets = [
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 3, 0),
            impressions=10.0,
            price_minor=700,
        ),
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 3, 15),
            impressions=20.0,
            price_minor=700,
        ),
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 3, 45),
            impressions=40.0,
            price_minor=700,
        ),
        BidBucketObservation(
            bid=100,
            bucket_start=datetime(2026, 6, 7, 4, 0),
            impressions=50.0,
            price_minor=700,
        ),
    ]

    result = build_hour_observations_from_buckets(buckets)

    assert result == []


def test_build_hour_observations_from_buckets_rejects_negative_impressions() -> None:
    buckets = _make_four_bucket_hour(700)
    buckets[1] = BidBucketObservation(
        bid=100,
        bucket_start=datetime(2026, 6, 7, 3, 15),
        impressions=-1.0,
        price_minor=700,
    )

    with pytest.raises(ValueError, match="bucket\\.impressions must be non-negative"):
        build_hour_observations_from_buckets(buckets)
