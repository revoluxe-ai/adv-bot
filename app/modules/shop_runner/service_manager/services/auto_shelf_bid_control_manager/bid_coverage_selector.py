"""Pure coverage-layer selection for Auto Shelf Bid Control test bids.

The module implements deterministic math for accumulated bid coverage layers.
It does not read state, analytics, or timestamps and can be integrated into the
manager later as a replacement for current cycle-window coverage logic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
import random
from typing import Sequence


@dataclass(frozen=True, slots=True)
class BidCoverage:
    """Accumulated coverage facts for a single bid point.

    Attributes:
        bid_minor: Bid value in minor units.
        impressions: Total valid impressions accumulated for the bid.
        valid_hours: Total valid hours accumulated for the bid.
    """

    bid_minor: int
    impressions: int
    valid_hours: int


def build_coverage_selector_seed(
    *,
    nmid: int,
    currency: str,
    price_minor: int | None,
    min_bid_minor: int,
    max_bid_minor: int,
    min_bid_distance_minor: int,
    target_test_impressions: int,
    target_test_observation_hours: int,
) -> int:
    """Build a deterministic seed for coverage-layer sampling."""
    payload = "|".join(
        [
            str(int(nmid)),
            str(currency),
            "none" if price_minor is None else str(int(price_minor)),
            str(int(min_bid_minor)),
            str(int(max_bid_minor)),
            str(int(min_bid_distance_minor)),
            str(int(target_test_impressions)),
            str(int(target_test_observation_hours)),
        ]
    )
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def build_bid_universe(
    min_bid_minor: int,
    max_bid_minor: int,
    *,
    bid_unit_minor: int = 100,
) -> list[int]:
    """Build a dense inclusive bid universe for coverage-layer accounting.

    Args:
        min_bid_minor: Lower bound of the bid universe.
        max_bid_minor: Upper bound of the bid universe.
        bid_unit_minor: Step of the dense bid grid.

    Returns:
        Inclusive dense bid universe or an empty list for an invalid range.

    Raises:
        ValueError: If ``bid_unit_minor`` is not positive.
    """
    if bid_unit_minor <= 0:
        raise ValueError("bid_unit_minor must be positive")
    if max_bid_minor < min_bid_minor:
        return []
    return list(range(int(min_bid_minor), int(max_bid_minor) + 1, int(bid_unit_minor)))


def closed_layers_for_bid(
    *,
    impressions: int,
    valid_hours: int,
    target_test_impressions: int,
    target_test_observation_hours: int,
) -> int:
    """Compute how many full coverage layers a bid has already closed.

    Args:
        impressions: Accumulated valid impressions for the bid.
        valid_hours: Accumulated valid hours for the bid.
        target_test_impressions: Required impressions to close one layer.
        target_test_observation_hours: Required valid hours to close one layer.

    Returns:
        Number of fully closed layers for the bid.

    Raises:
        ValueError: If either target is not positive.
    """
    if target_test_impressions <= 0:
        raise ValueError("target_test_impressions must be positive")
    if target_test_observation_hours <= 0:
        raise ValueError("target_test_observation_hours must be positive")
    return min(
        int(impressions) // int(target_test_impressions),
        int(valid_hours) // int(target_test_observation_hours),
    )


def _coverage_by_bid(coverages: Sequence[BidCoverage]) -> dict[int, BidCoverage]:
    """Normalize coverage rows into a deterministic map keyed by bid."""
    return {int(item.bid_minor): item for item in coverages}


def _choose_undercovered_bid(
    *,
    undercovered_bids: Sequence[int],
    covered_ahead_bids: Sequence[int],
    min_bid_distance_minor: int,
    random_seed: int | None,
) -> int | None:
    """Pick one bid from the under-covered set.

    Randomness is allowed only for the first bid of a coverage layer, when
    there are no better-covered anchor bids yet. Once anchors exist, selection
    becomes distance-driven: choose the under-covered bid that is farthest from
    the nearest covered anchor. ``min_bid_distance_minor`` still does not alter
    coverage math and applies only as a final candidate filter if it leaves at
    least one candidate.
    """
    if not undercovered_bids:
        return None
    ordered_undercovered = sorted(int(bid) for bid in undercovered_bids)
    rng = random.Random(random_seed)
    if not covered_ahead_bids:
        return rng.choice(ordered_undercovered)
    ordered_ahead = sorted(int(bid) for bid in covered_ahead_bids)
    distance_by_bid = {
        bid: min(abs(bid - other) for other in ordered_ahead)
        for bid in ordered_undercovered
    }
    candidates = ordered_undercovered
    filtered_candidates = [
        bid
        for bid in ordered_undercovered
        if distance_by_bid[bid] >= int(min_bid_distance_minor)
    ]
    if filtered_candidates:
        candidates = filtered_candidates
    max_distance = max(distance_by_bid[bid] for bid in candidates)
    farthest_candidates = [
        bid for bid in candidates if distance_by_bid[bid] == max_distance
    ]
    if len(farthest_candidates) == 1:
        return farthest_candidates[0]
    return rng.choice(farthest_candidates)


def choose_next_test_bid_by_coverage_layers(
    *,
    min_bid_minor: int,
    max_bid_minor: int,
    bid_unit_minor: int,
    coverages: Sequence[BidCoverage],
    target_test_impressions: int,
    target_test_observation_hours: int,
    min_bid_distance_minor: int,
    random_seed: int | None = None,
) -> int | None:
    """Choose the next test bid from the current under-covered layer.

    The function computes closed layers over the full dense universe
    ``[min_bid_minor, max_bid_minor]`` with step ``bid_unit_minor``. Missing
    bids are treated as zero-covered points.

    Args:
        min_bid_minor: Lower bound of the dense bid universe.
        max_bid_minor: Upper bound of the dense bid universe.
        bid_unit_minor: Universe step in minor units.
        coverages: Accumulated coverage rows for any subset of the universe.
        target_test_impressions: Required impressions for one full layer.
        target_test_observation_hours: Required valid hours for one full layer.
        min_bid_distance_minor: Final-selection spacing rule. It must not affect
            coverage calculation and only filters final random candidates.
        random_seed: Optional seed for reproducible local random selection.

    Returns:
        Selected next test bid or ``None`` for an invalid range / empty universe.

    Raises:
        ValueError: If ``bid_unit_minor`` or target thresholds are not positive.
    """
    universe = build_bid_universe(
        min_bid_minor,
        max_bid_minor,
        bid_unit_minor=bid_unit_minor,
    )
    if not universe:
        return None
    coverage_map = _coverage_by_bid(coverages)
    closed_layers_by_bid: dict[int, int] = {}
    for bid in universe:
        coverage = coverage_map.get(
            bid,
            BidCoverage(bid_minor=bid, impressions=0, valid_hours=0),
        )
        closed_layers_by_bid[bid] = closed_layers_for_bid(
            impressions=coverage.impressions,
            valid_hours=coverage.valid_hours,
            target_test_impressions=target_test_impressions,
            target_test_observation_hours=target_test_observation_hours,
        )
    current_layer = min(closed_layers_by_bid.values())
    undercovered_bids = [
        bid for bid in universe if closed_layers_by_bid[bid] == current_layer
    ]
    covered_ahead_bids = [
        bid for bid in universe if closed_layers_by_bid[bid] > current_layer
    ]
    return _choose_undercovered_bid(
        undercovered_bids=undercovered_bids,
        covered_ahead_bids=covered_ahead_bids,
        min_bid_distance_minor=int(min_bid_distance_minor),
        random_seed=random_seed,
    )
