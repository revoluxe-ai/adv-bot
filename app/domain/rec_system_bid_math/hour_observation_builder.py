"""Построение hour-level наблюдений из 15-минутных bucket-ов.

Модуль остаётся чистым и не знает ничего о DB, ClickHouse или сервисных слоях.
Он принимает уже подготовленные bucket-строки и собирает из них валидные
часовые наблюдения для bid-math модели.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from app.domain.rec_system_bid_math.input_models import BidHourObservation

BUCKET_MINUTES = (0, 15, 30, 45)


@dataclass(frozen=True)
class BidBucketObservation:
    """Одна 15-минутная наблюдаемая точка для одной ставки."""

    bid: int
    bucket_start: datetime
    impressions: float
    price_minor: int | None = None


def build_hour_observations_from_buckets(
    buckets: list[BidBucketObservation],
) -> list[BidHourObservation]:
    """Собрать почасовые наблюдения из 15-минутных bucket-ов.

    Валидный час требует ровно четыре bucket-а по сетке 00/15/30/45 минут.
    Неполные часы и группы с отрицательными impressions пропускаются.
    """
    grouped: dict[tuple[int, datetime], list[BidBucketObservation]] = defaultdict(list)
    for bucket in buckets:
        grouped[
            (
                bucket.bid,
                bucket.bucket_start.replace(minute=0, second=0, microsecond=0),
            )
        ].append(bucket)

    result: list[BidHourObservation] = []
    for (bid, hour_start), group in grouped.items():
        if len(group) != 4:
            continue

        if any(bucket.impressions < 0 for bucket in group):
            raise ValueError("bucket.impressions must be non-negative")

        price_values = {bucket.price_minor for bucket in group}
        if len(price_values) != 1:
            continue

        sorted_group = sorted(group, key=lambda item: item.bucket_start)
        if [bucket.bucket_start.minute for bucket in sorted_group] != list(BUCKET_MINUTES):
            continue

        if any(
            bucket.bucket_start.hour != hour_start.hour
            or bucket.bucket_start.minute != expected_minute
            for bucket, expected_minute in zip(sorted_group, BUCKET_MINUTES)
        ):
            continue

        result.append(
            BidHourObservation(
                bid=bid,
                hour=hour_start.hour,
                impressions_sum=sum(bucket.impressions for bucket in group),
                valid_hours_count=1,
            )
        )

    return result
