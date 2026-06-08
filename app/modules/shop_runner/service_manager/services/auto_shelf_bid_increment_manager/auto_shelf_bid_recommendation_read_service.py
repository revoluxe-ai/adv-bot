"""Read-only orchestration for bid recommendation ranking.

Сервис только читает bucket rows, собирает hour-level наблюдения и строит
ranked list без любых побочных эффектов для ставок.
"""

from __future__ import annotations

import logging
from datetime import datetime
from collections import Counter
from collections.abc import Sequence
from typing import Any, Protocol, cast

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
    build_hour_observations_from_buckets,
)
from app.domain.rec_system_bid_math.input_models import BidHourObservation
from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.domain.rec_system_bid_math.service import rank_rec_system_bids
from app.domain.rec_system_bid_math.view_models import (
    build_rec_bid_recommendation_view,
)

from app.domain.rec_system_bid_math.hour_observation_builder import BUCKET_MINUTES

logger = logging.getLogger(__name__)


class RecBidRecommendationRepository(Protocol):
    """Минимальный контракт CH-read репозитория для rec bid recommendation."""

    async def fetch_rec_bid_bucket_observations_for_nmid(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[BidBucketObservation]:
        """Вернуть bucket-строки для hour-level recommendation."""
        ...

    async def fetch_rec_bid_ctr_by_bid_for_nmid(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
    ) -> dict[int, float]:
        """Вернуть CTR по bid для recommendation."""
        ...


def _bucket_reason_counts(buckets: list[BidBucketObservation]) -> dict[str, int]:
    grouped: dict[tuple[int, datetime], list[BidBucketObservation]] = {}
    for bucket in buckets:
        grouped.setdefault(
            (
                bucket.bid,
                bucket.bucket_start.replace(minute=0, second=0, microsecond=0),
            ),
            [],
        ).append(bucket)

    counts: Counter[str] = Counter()
    for group in grouped.values():
        bid_values = {bucket.bid for bucket in group}
        price_values = {bucket.price_minor for bucket in group}
        if len(bid_values) > 1:
            counts["multiple_bid"] += 1
            continue
        if len(price_values) > 1:
            counts["multiple_price"] += 1
            continue
        if sum(bucket.impressions for bucket in group) < 0:
            counts["negative_impressions"] += 1
    return dict(counts)


def _hour_reason_counts(
    buckets: Sequence[BidBucketObservation],
    observations: Sequence[BidHourObservation],
) -> dict[str, int]:
    grouped: dict[tuple[int, datetime], list[BidBucketObservation]] = {}
    for bucket in buckets:
        grouped.setdefault(
            (
                bucket.bid,
                bucket.bucket_start.replace(minute=0, second=0, microsecond=0),
            ),
            [],
        ).append(bucket)

    valid_hour_keys: set[tuple[int, int]] = {
        (observation.bid, observation.hour) for observation in observations
    }
    counts: Counter[str] = Counter()
    for (bid, hour_start), group in grouped.items():
        if len(group) != 4:
            counts["missing_bucket"] += 1
            continue
        if len({bucket.bid for bucket in group}) > 1:
            counts["multiple_bid"] += 1
            continue
        if len({bucket.price_minor for bucket in group}) > 1:
            counts["multiple_price"] += 1
            continue
        sorted_group = sorted(group, key=lambda item: item.bucket_start)
        if [bucket.bucket_start.minute for bucket in sorted_group] != list(BUCKET_MINUTES):
            counts["bad_grid"] += 1
            continue
        if (bid, hour_start.hour) not in valid_hour_keys:
            counts["missing_bucket"] += 1
    return dict(counts)


def _validate_ctr_by_bid(
    observations: Sequence[BidHourObservation],
    ctr_by_bid: dict[int, float],
) -> None:
    """Ensure every observed bid has CTR data before ranking."""
    observed_bids = {observation.bid for observation in observations}
    missing_bids = sorted(observed_bids - ctr_by_bid.keys())
    if missing_bids:
        raise ValueError(f"Missing CTR for bids: {missing_bids}")


def _empty_recommendation_payload(
    *,
    diagnostics: dict[str, Any],
) -> dict[str, object]:
    """Build stable empty recommendation payload."""
    bid_result: dict[str, object] = {
        "rows": [],
        "expected_ranked": [],
        "main_ranked": [],
        "test_ranked": [],
        "debug": {},
        "y_obs": {},
        "c_obs": {},
        "y_final": {},
        "c_final": {},
    }
    result: dict[str, object] = {
        "bid_result": bid_result,
        "plan_ranked": [],
        "best_plan_bid": None,
        "best_expected_bid": None,
        "diagnostics": diagnostics,
    }
    result["view"] = build_rec_bid_recommendation_view(result)
    return result


class AutoShelfBidRecommendationReadService:
    """Читает bucket rows и строит ranked result без записи в БД."""

    def __init__(self, repository: RecBidRecommendationRepository) -> None:
        self._repository = repository

    async def fetch_bid_hour_observation_diagnostics(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
    ) -> dict[str, Any]:
        """Вернуть диагностику качества bucket/hour read-path без ранжирования."""
        buckets = await self._repository.fetch_rec_bid_bucket_observations_for_nmid(
            nmid=nmid,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
        )
        observations = build_hour_observations_from_buckets(buckets)
        distinct_bids = len({bucket.bid for bucket in buckets})
        bucket_reason_counts = _bucket_reason_counts(buckets)
        hour_reason_counts = _hour_reason_counts(buckets, observations)
        valid_bucket_count = len(buckets)
        invalid_bucket_count = 0
        valid_hour_count = len(observations)
        invalid_hour_count = max(0, len(buckets) - valid_hour_count)
        return {
            "raw_rows_count": len(buckets),
            "valid_bucket_count": valid_bucket_count,
            "invalid_bucket_count": invalid_bucket_count,
            "invalid_bucket_reason_counts": bucket_reason_counts,
            "valid_hour_count": valid_hour_count,
            "invalid_hour_count": invalid_hour_count,
            "invalid_hour_reason_counts": hour_reason_counts,
            "observations_count": len(observations),
            "distinct_bids": distinct_bids,
            "date_from": date_from,
            "date_to": date_to,
        }

    async def fetch_and_rank_rec_system_bids_for_nmid(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
        plan_context: PlanContext,
        ctr_by_bid: dict[int, float],
    ) -> dict[str, Any]:
        """Собрать observation chain и вернуть ranked result."""
        buckets = await self._repository.fetch_rec_bid_bucket_observations_for_nmid(
            nmid=nmid,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
        )
        observations = build_hour_observations_from_buckets(buckets)
        diagnostics = {
            "bucket_count": len(buckets),
            "hour_observation_count": len(observations),
            "bid_count": len({bucket.bid for bucket in buckets}),
            "hour_count": len({obs.hour for obs in observations}),
        }
        if not observations:
            return _empty_recommendation_payload(diagnostics=diagnostics)
        _validate_ctr_by_bid(observations, ctr_by_bid)
        result = rank_rec_system_bids(
            observations=observations,
            plan_context=plan_context,
            ctr_by_bid=ctr_by_bid,
        )
        result["diagnostics"] = diagnostics
        result["view"] = build_rec_bid_recommendation_view(result)
        return result

    async def get_rec_bid_recommendations(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
        plan_context: PlanContext,
        ctr_by_bid: dict[int, float],
    ) -> dict[str, Any]:
        """Return full read-only ranking payload for a rec bid source."""
        buckets = await self._repository.fetch_rec_bid_bucket_observations_for_nmid(
            nmid=nmid,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
        )
        observations = build_hour_observations_from_buckets(buckets)
        diagnostics = {
            "bucket_count": len(buckets),
            "hour_observation_count": len(observations),
            "bid_count": len({bucket.bid for bucket in buckets}),
            "hour_count": len({obs.hour for obs in observations}),
        }
        if not observations:
            return _empty_recommendation_payload(diagnostics=diagnostics)
        _validate_ctr_by_bid(observations, ctr_by_bid)
        result: dict[str, object] = rank_rec_system_bids(
            observations=observations,
            plan_context=plan_context,
            ctr_by_bid=ctr_by_bid,
        )
        bid_result = cast(dict[str, object], result["bid_result"])
        expected_ranked = cast(list[dict[str, object]], bid_result["expected_ranked"])
        plan_ranked = cast(list[dict[str, object]], result["plan_ranked"])
        full_result: dict[str, object] = {
            "bid_result": bid_result,
            "plan_ranked": plan_ranked,
            "best_plan_bid": plan_ranked[0]["bid"] if plan_ranked else None,
            "best_expected_bid": (
                expected_ranked[0]["bid"] if expected_ranked
                else None
            ),
            "diagnostics": diagnostics,
        }
        full_result["view"] = build_rec_bid_recommendation_view(full_result)
        return full_result

    @staticmethod
    def _top10(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return rows[:10]

    async def debug_fetch_and_rank_rec_system_bids_for_nmid(
        self,
        nmid: int,
        mode: str,
        date_from: datetime,
        date_to: datetime,
        plan_context: PlanContext,
        ctr_by_bid: dict[int, float],
    ) -> dict[str, Any]:
        """Read-only debug entrypoint: diagnostics + ranked top-10 logs."""
        diagnostics = await self.fetch_bid_hour_observation_diagnostics(
            nmid=nmid,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.fetch_and_rank_rec_system_bids_for_nmid(
            nmid=nmid,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
            plan_context=plan_context,
            ctr_by_bid=ctr_by_bid,
        )
        expected_ranked = self._top10(result["bid_result"]["expected_ranked"])
        main_ranked = self._top10(result["bid_result"]["main_ranked"])
        test_ranked = self._top10(result["bid_result"]["test_ranked"])
        plan_ranked = self._top10(result["plan_ranked"])
        logger.info("auto_shelf_bid_debug diagnostics=%s", diagnostics)
        logger.info("auto_shelf_bid_debug expected_ranked_top10=%s", expected_ranked)
        logger.info("auto_shelf_bid_debug main_ranked_top10=%s", main_ranked)
        logger.info("auto_shelf_bid_debug test_ranked_top10=%s", test_ranked)
        logger.info("auto_shelf_bid_debug plan_ranked_top10=%s", plan_ranked)
        return {
            "diagnostics": diagnostics,
            "bid_result": result["bid_result"],
            "plan_ranked": result["plan_ranked"],
        }
