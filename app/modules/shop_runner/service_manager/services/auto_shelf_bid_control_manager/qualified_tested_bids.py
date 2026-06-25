"""Квалифицированные протестированные ставки для main recommendation gate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from .bid_selection import pick_better_bid_by_cart_cpa, pick_better_bid_by_ctr
from .dto.bid_stats_dto import BidStatsDTO
from .dto.decision_snapshot_dto import parse_plan_ranked_top_bid_minor
from .dto.optimization_metric import OptimizationMetric

MIN_QUALIFIED_TESTED_BIDS_FOR_MAIN = 2

INSUFFICIENT_QUALIFIED_TESTED_BIDS_EXPLANATION = (
    "недостаточно протестированных ставок"
)


def _coerce_str_object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    mapping = cast(Mapping[object, object], value)
    return {str(key): val for key, val in mapping.items()}


def _coerce_object_sequence(value: object) -> Sequence[object] | None:
    if isinstance(value, (str, bytes, bytearray)):
        return None
    if isinstance(value, Sequence):
        return cast(Sequence[object], value)
    return None


def collect_qualified_tested_bid_minors(
    cycle_bid_stats: Sequence[BidStatsDTO],
    *,
    target_test_impressions: int,
    metric: OptimizationMetric,
) -> list[int]:
    """Уникальные ставки цикла с достаточным числом показов для test-порога."""
    qualified: set[int] = set()
    for item in cycle_bid_stats:
        if item.impressions < target_test_impressions:
            continue
        if metric == OptimizationMetric.CPC and item.clicks <= 0:
            continue
        qualified.add(int(item.bid_minor))
    return sorted(qualified)


def count_qualified_tested_bids(
    cycle_bid_stats: Sequence[BidStatsDTO],
    *,
    target_test_impressions: int,
    metric: OptimizationMetric,
) -> int:
    """Число квалифицированных протестированных ставок в текущем цикле."""
    return len(
        collect_qualified_tested_bid_minors(
            cycle_bid_stats,
            target_test_impressions=target_test_impressions,
            metric=metric,
        )
    )


def has_sufficient_qualified_tested_bids(
    cycle_bid_stats: Sequence[BidStatsDTO],
    *,
    target_test_impressions: int,
    metric: OptimizationMetric,
) -> bool:
    """Main recommendation разрешена только при >= 2 qualified tested bids."""
    return (
        count_qualified_tested_bids(
            cycle_bid_stats,
            target_test_impressions=target_test_impressions,
            metric=metric,
        )
        >= MIN_QUALIFIED_TESTED_BIDS_FOR_MAIN
    )


def rank_qualified_tested_bid_stats(
    cycle_bid_stats: Sequence[BidStatsDTO],
    *,
    target_test_impressions: int,
    metric: OptimizationMetric,
) -> list[BidStatsDTO]:
    """Qualified tested bids, отсортированные по метрике оптимизации (лучший первый)."""
    by_bid: dict[int, BidStatsDTO] = {}
    for item in cycle_bid_stats:
        if item.impressions < target_test_impressions:
            continue
        if metric == OptimizationMetric.CPC and item.clicks <= 0:
            continue
        current = by_bid.get(int(item.bid_minor))
        if current is None:
            by_bid[int(item.bid_minor)] = item
            continue
        better = (
            pick_better_bid_by_ctr(current, item)
            if metric == OptimizationMetric.CTR
            else pick_better_bid_by_cart_cpa(current, item)
        )
        if better is not None:
            by_bid[int(item.bid_minor)] = better

    items = list(by_bid.values())
    if metric == OptimizationMetric.CTR:
        items.sort(
            key=lambda row: (
                -(row.ctr if row.ctr is not None else float("-inf")),
                int(row.bid_minor),
            )
        )
    else:
        items.sort(
            key=lambda row: (
                row.cart_cpa if row.cart_cpa is not None else float("inf"),
                int(row.bid_minor),
            )
        )
    return items


def build_plan_ranked_rows_from_bid_stats(
    ranked_stats: Sequence[BidStatsDTO],
    *,
    limit: int = 3,
) -> list[dict[str, object]]:
    """Нормализовать ranked stats в ``plan_ranked`` rows для snapshot/UI."""
    rows: list[dict[str, object]] = []
    for item in ranked_stats[:limit]:
        row: dict[str, object] = {
            "bid": int(item.bid_minor),
            "impressions": int(item.impressions),
            "clicks": int(item.clicks),
            "carts": int(item.carts),
            "orders": int(item.orders),
            "spend": float(item.spend),
        }
        if item.ctr is not None:
            row["ctr"] = float(item.ctr)
        if item.cart_cpa is not None:
            row["cpc"] = float(item.cart_cpa)
        rows.append(row)
    return rows


def filter_rec_recommendation_to_qualified_bids(
    recommendation: Mapping[str, object] | None,
    qualified_bid_minors: Sequence[int],
) -> dict[str, object] | None:
    """Оставить в ``plan_ranked`` только квалифицированные протестированные ставки."""
    if recommendation is None:
        return None
    qualified_set = {int(bid) for bid in qualified_bid_minors}
    plan_ranked_raw = recommendation.get("plan_ranked")
    rows = _coerce_object_sequence(plan_ranked_raw) or []
    filtered: list[dict[str, object]] = []
    for row_raw in rows:
        row = _coerce_str_object_dict(row_raw)
        if row is None:
            continue
        bid_raw = row.get("bid")
        if (
            isinstance(bid_raw, int)
            and not isinstance(bid_raw, bool)
            and int(bid_raw) in qualified_set
        ):
            filtered.append(dict(row))
    result = {str(key): value for key, value in recommendation.items()}
    result["plan_ranked"] = filtered
    return result


def build_cycle_metric_rec_recommendation(
    ranked_stats: Sequence[BidStatsDTO],
) -> dict[str, object]:
    """Собрать rec view для CYCLE_METRIC из qualified tested ranking."""
    return {
        "plan_ranked": build_plan_ranked_rows_from_bid_stats(ranked_stats),
        "ranking_source": "cycle_metric",
    }


def resolve_main_bid_from_qualified_ranking(
    recommendation: Mapping[str, object] | None,
    *,
    min_bid_minor: int,
    max_bid_minor: int,
) -> tuple[int | None, int | None, str | None]:
    """Вернуть (fresh_main, ranked_top_raw, clamp_explanation) из qualified plan_ranked."""
    ranked_top = parse_plan_ranked_top_bid_minor(recommendation)
    if ranked_top is None:
        return None, None, None
    clamped = max(int(min_bid_minor), min(int(max_bid_minor), int(ranked_top)))
    explanation: str | None = None
    if clamped != int(ranked_top):
        explanation = f"clamp_to_range: {ranked_top} -> {clamped}"
    return clamped, int(ranked_top), explanation


__all__ = [
    "MIN_QUALIFIED_TESTED_BIDS_FOR_MAIN",
    "INSUFFICIENT_QUALIFIED_TESTED_BIDS_EXPLANATION",
    "build_cycle_metric_rec_recommendation",
    "build_plan_ranked_rows_from_bid_stats",
    "collect_qualified_tested_bid_minors",
    "count_qualified_tested_bids",
    "filter_rec_recommendation_to_qualified_bids",
    "has_sufficient_qualified_tested_bids",
    "rank_qualified_tested_bid_stats",
    "resolve_main_bid_from_qualified_ranking",
]
