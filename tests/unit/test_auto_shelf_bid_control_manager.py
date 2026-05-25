from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)


pytestmark = pytest.mark.unit


def test_choose_next_test_bid_without_covered_returns_middle() -> None:
    bid = AutoShelfBidControlManager.choose_next_test_bid(
        min_bid=1000,
        max_bid=5000,
        covered_bids=[],
        min_distance=100,
    )
    assert bid == 3000


def test_choose_next_test_bid_picks_max_distance_point() -> None:
    bid = AutoShelfBidControlManager.choose_next_test_bid(
        min_bid=1000,
        max_bid=5000,
        covered_bids=[2000, 3000, 4000],
        min_distance=100,
    )
    # На равных расстояниях выбирается меньшая ставка.
    assert bid == 1000


def test_choose_next_test_bid_returns_none_when_range_is_covered() -> None:
    bid = AutoShelfBidControlManager.choose_next_test_bid(
        min_bid=1000,
        max_bid=5000,
        covered_bids=[1000, 3000, 5000],
        min_distance=1500,
    )
    assert bid is None


def test_calc_target_main_impressions_with_valid_share() -> None:
    target = AutoShelfBidControlManager._calc_target_main_impressions(500, 0.1)
    assert target == 4500


def test_calc_target_main_impressions_invalid_share_returns_none() -> None:
    assert AutoShelfBidControlManager._calc_target_main_impressions(500, 0) is None
    assert AutoShelfBidControlManager._calc_target_main_impressions(500, 0.5) is None


def test_is_coroutine_candidate_requires_enabled_single_nmid_and_active() -> None:
    from types import SimpleNamespace

    ok = SimpleNamespace(
        auto_shelf_bid_control_enabled=True,
        nmids=[1],
        bot_active=True,
        auto_adv_active_status=True,
        auto_adv_id=99,
    )
    assert AutoShelfBidControlManager.is_coroutine_candidate(ok) is True

    disabled = SimpleNamespace(
        auto_shelf_bid_control_enabled=False,
        nmids=[1],
        bot_active=True,
        auto_adv_active_status=True,
        auto_adv_id=99,
    )
    assert AutoShelfBidControlManager.is_coroutine_candidate(disabled) is False

