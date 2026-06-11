"""Unit tests for pure accumulated bid coverage-layer selection."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_coverage_selector import (
    BidCoverage,
    build_bid_universe,
    choose_next_test_bid_by_coverage_layers,
    closed_layers_for_bid,
)


pytestmark = pytest.mark.unit


def test_build_bid_universe_dense_range() -> None:
    assert build_bid_universe(12_000, 12_300, bid_unit_minor=100) == [
        12_000,
        12_100,
        12_200,
        12_300,
    ]


def test_missing_coverage_means_zero_layers() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_200,
        bid_unit_minor=100,
        coverages=[BidCoverage(bid_minor=12_100, impressions=2_000, valid_hours=1)],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=1,
    )
    assert chosen in {12_000, 12_200}


def test_closed_layers_zero_when_impressions_enough_but_hours_not_enough() -> None:
    assert (
        closed_layers_for_bid(
            impressions=4_000,
            valid_hours=0,
            target_test_impressions=2_000,
            target_test_observation_hours=1,
        )
        == 0
    )


def test_closed_layers_zero_when_hours_enough_but_impressions_not_enough() -> None:
    assert (
        closed_layers_for_bid(
            impressions=1_000,
            valid_hours=3,
            target_test_impressions=2_000,
            target_test_observation_hours=1,
        )
        == 0
    )


def test_closed_layers_counts_full_layers() -> None:
    assert (
        closed_layers_for_bid(
            impressions=4_000,
            valid_hours=2,
            target_test_impressions=2_000,
            target_test_observation_hours=1,
        )
        == 2
    )


def test_current_layer_uses_full_dense_universe_including_missing_bids() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_300,
        bid_unit_minor=100,
        coverages=[
            BidCoverage(bid_minor=12_100, impressions=4_000, valid_hours=2),
            BidCoverage(bid_minor=12_200, impressions=4_000, valid_hours=2),
            BidCoverage(bid_minor=12_300, impressions=4_000, valid_hours=2),
        ],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=1,
    )
    assert chosen == 12_000


def test_overcovered_bid_is_skipped() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_200,
        bid_unit_minor=100,
        coverages=[
            BidCoverage(bid_minor=12_000, impressions=4_000, valid_hours=2),
            BidCoverage(bid_minor=12_100, impressions=0, valid_hours=0),
            BidCoverage(bid_minor=12_200, impressions=8_000, valid_hours=4),
        ],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=1,
    )
    assert chosen == 12_100


def test_selected_bid_is_always_from_undercovered_bids() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_300,
        bid_unit_minor=100,
        coverages=[
            BidCoverage(bid_minor=12_000, impressions=2_000, valid_hours=1),
            BidCoverage(bid_minor=12_200, impressions=2_000, valid_hours=1),
        ],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=7,
    )
    assert chosen in {12_100, 12_300}


def test_min_bid_distance_does_not_remove_bids_from_coverage_universe() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_200,
        bid_unit_minor=100,
        coverages=[BidCoverage(bid_minor=12_100, impressions=2_000, valid_hours=1)],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=10_000,
        random_seed=1,
    )
    assert chosen in {12_000, 12_200}


def test_distance_filtered_candidates_are_preferred_when_available() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_400,
        bid_unit_minor=100,
        coverages=[
            BidCoverage(bid_minor=12_200, impressions=2_000, valid_hours=1),
            BidCoverage(bid_minor=12_300, impressions=2_000, valid_hours=1),
        ],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=150,
        random_seed=1,
    )
    assert chosen in {12_000, 12_400}


def test_distance_filtered_candidates_fallback_to_all_undercovered_when_empty() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_400,
        bid_unit_minor=100,
        coverages=[BidCoverage(bid_minor=12_200, impressions=2_000, valid_hours=1)],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=10_000,
        random_seed=1,
    )
    assert chosen in {12_000, 12_100, 12_300, 12_400}


def test_same_random_seed_returns_same_bid() -> None:
    kwargs = dict(
        min_bid_minor=12_000,
        max_bid_minor=12_400,
        bid_unit_minor=100,
        coverages=[BidCoverage(bid_minor=12_200, impressions=2_000, valid_hours=1)],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=10_000,
        random_seed=42,
    )
    first = choose_next_test_bid_by_coverage_layers(**kwargs)
    second = choose_next_test_bid_by_coverage_layers(**kwargs)
    assert first == second


def test_different_random_seed_can_return_different_bid_for_first_layer() -> None:
    kwargs = dict(
        min_bid_minor=12_000,
        max_bid_minor=12_300,
        bid_unit_minor=100,
        coverages=[],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
    )
    first = choose_next_test_bid_by_coverage_layers(random_seed=1, **kwargs)
    second = choose_next_test_bid_by_coverage_layers(random_seed=5, **kwargs)
    assert first != second


def test_first_layer_with_no_covered_anchors_uses_seeded_random() -> None:
    kwargs = dict(
        min_bid_minor=12_000,
        max_bid_minor=12_300,
        bid_unit_minor=100,
        coverages=[],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=42,
    )
    first = choose_next_test_bid_by_coverage_layers(**kwargs)
    second = choose_next_test_bid_by_coverage_layers(**kwargs)
    assert first in {12_000, 12_100, 12_200, 12_300}
    assert first == second


def test_covered_anchor_prefers_farthest_undercovered_bid() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=16_200,
        max_bid_minor=60_000,
        bid_unit_minor=100,
        coverages=[BidCoverage(bid_minor=16_200, impressions=2_000, valid_hours=1)],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=1,
    )
    assert chosen == 60_000
    assert chosen != 16_300


def test_multiple_anchors_choose_farthest_undercovered_region() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=60_000,
        bid_unit_minor=100,
        coverages=[
            BidCoverage(bid_minor=12_000, impressions=2_000, valid_hours=1),
            BidCoverage(bid_minor=24_000, impressions=2_000, valid_hours=1),
        ],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=1,
    )
    assert chosen == 60_000


def test_min_bid_distance_filters_final_candidates_only_when_possible() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_400,
        bid_unit_minor=100,
        coverages=[
            BidCoverage(bid_minor=12_000, impressions=2_000, valid_hours=1),
            BidCoverage(bid_minor=12_400, impressions=2_000, valid_hours=1),
        ],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=150,
        random_seed=1,
    )
    assert chosen == 12_200


def test_min_bid_distance_fallback_keeps_all_undercovered_when_filter_empty() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=12_200,
        bid_unit_minor=100,
        coverages=[BidCoverage(bid_minor=12_100, impressions=2_000, valid_hours=1)],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=10_000,
        random_seed=1,
    )
    assert chosen in {12_000, 12_200}


def test_selected_bid_is_always_aligned_to_bid_unit() -> None:
    chosen = choose_next_test_bid_by_coverage_layers(
        min_bid_minor=12_000,
        max_bid_minor=60_000,
        bid_unit_minor=100,
        coverages=[BidCoverage(bid_minor=16_200, impressions=2_000, valid_hours=1)],
        target_test_impressions=2_000,
        target_test_observation_hours=1,
        min_bid_distance_minor=100,
        random_seed=5,
    )
    assert chosen is not None
    assert chosen % 100 == 0


def test_invalid_inputs_raise_or_return_none() -> None:
    with pytest.raises(ValueError):
        build_bid_universe(12_000, 12_300, bid_unit_minor=0)
    with pytest.raises(ValueError):
        closed_layers_for_bid(
            impressions=1,
            valid_hours=1,
            target_test_impressions=0,
            target_test_observation_hours=1,
        )
    with pytest.raises(ValueError):
        choose_next_test_bid_by_coverage_layers(
            min_bid_minor=12_000,
            max_bid_minor=12_300,
            bid_unit_minor=0,
            coverages=[],
            target_test_impressions=2_000,
            target_test_observation_hours=1,
            min_bid_distance_minor=100,
            random_seed=1,
        )
    with pytest.raises(ValueError):
        choose_next_test_bid_by_coverage_layers(
            min_bid_minor=12_000,
            max_bid_minor=12_300,
            bid_unit_minor=100,
            coverages=[],
            target_test_impressions=0,
            target_test_observation_hours=1,
            min_bid_distance_minor=100,
            random_seed=1,
        )
    with pytest.raises(ValueError):
        choose_next_test_bid_by_coverage_layers(
            min_bid_minor=12_000,
            max_bid_minor=12_300,
            bid_unit_minor=100,
            coverages=[],
            target_test_impressions=2_000,
            target_test_observation_hours=0,
            min_bid_distance_minor=100,
            random_seed=1,
        )
    assert (
        choose_next_test_bid_by_coverage_layers(
            min_bid_minor=12_300,
            max_bid_minor=12_000,
            bid_unit_minor=100,
            coverages=[],
            target_test_impressions=2_000,
            target_test_observation_hours=1,
            min_bid_distance_minor=100,
            random_seed=1,
        )
        is None
    )
