"""Shared mapper from ClickHouse bucket rows to rec-system bid bucket observations.

The module intentionally contains no repository or database access code.
It only converts raw ClickHouse rows into domain DTOs used by both rec-bid and
control analytics read paths.
"""

from __future__ import annotations

from datetime import datetime
from collections.abc import Mapping, Sequence
from typing import Any, cast

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
)


def build_bid_bucket_observations_from_ch_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[BidBucketObservation]:
    """Build 15-minute bucket observations from ClickHouse rows.

    Rows are grouped by the full bucket context:
        (bucket_start, bid_minor/bid, price_minor).
    The function keeps the current contract for rec-bid/control read paths and
    leaves hour-level validation to the hour builder.
    """
    grouped: dict[tuple[datetime, int, int | None], list[Mapping[str, object]]] = {}
    for row in rows:
        bucket_start = row.get("bucket_start")
        if not isinstance(bucket_start, datetime):
            raise KeyError("row is missing bucket_start")
        bid_value = row.get("bid_minor", row.get("bid"))
        if bid_value is None:
            raise KeyError("row is missing bid_minor/bid")
        price_value = row.get("price_minor")
        key = (
            bucket_start,
            int(cast(Any, bid_value)),
            None if price_value is None else int(cast(Any, price_value)),
        )
        grouped.setdefault(key, []).append(row)

    observations: list[BidBucketObservation] = []
    for (bucket_start, bid_minor, price_minor), bucket_rows in grouped.items():
        impressions_sum = 0.0
        for row in bucket_rows:
            impressions_value = row.get("delta_impressions", row.get("impressions"))
            if impressions_value is None:
                raise KeyError("row is missing delta_impressions/impressions")
            impressions_sum += float(cast(Any, impressions_value))

        if impressions_sum < 0:
            continue

        observations.append(
            BidBucketObservation(
                bid=bid_minor,
                bucket_start=bucket_start,
                impressions=impressions_sum,
                price_minor=price_minor,
            )
        )

    return observations
