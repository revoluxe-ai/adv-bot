from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    BidStatsDTO,
)


pytestmark = pytest.mark.unit


def test_clamp_bid_minor_within_window() -> None:
    assert (
        AutoShelfBidControlManager._clamp_bid_minor(
            25_000,
            min_bid_minor=12_000,
            max_bid_minor=50_000,
        )
        == 25_000
    )
    assert (
        AutoShelfBidControlManager._clamp_bid_minor(
            99_000,
            min_bid_minor=12_000,
            max_bid_minor=50_000,
        )
        == 50_000
    )
    assert (
        AutoShelfBidControlManager._clamp_bid_minor(
            5_000,
            min_bid_minor=12_000,
            max_bid_minor=50_000,
        )
        == 12_000
    )


@pytest.mark.asyncio
async def test_choose_best_bid_clamps_historical_ch_bid() -> None:
    analytics = MagicMock()
    analytics.get_best_bid_by_cart_cpa = AsyncMock(
        return_value=BidStatsDTO(
            bid_minor=99_000,
            currency="RUB",
            mode=None,
            last_interval_at=None,
            impressions=1000,
            clicks=10,
            carts=5,
            orders=0,
            spend=100.0,
            cart_cpa=20.0,
            ctr=0.01,
            cart_cr=0.5,
        )
    )
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        analytics_repository=analytics,
    )
    result = await manager._choose_best_bid_with_fallback(
        nmid=1,
        currency="RUB",
        cycle_started_at=datetime.now(timezone.utc),
        previous_cycle_started_at=None,
        current_main_bid_minor=None,
        actual_bid_minor=None,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
    )
    assert result == 50_000


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


def test_choose_next_test_bid_full_cycle_coverage_picks_280_not_covered_bid() -> None:
    """Все точки цикла покрыты — следующая ставка в зазоре 200–360, не 360."""
    covered = [12_000, 20_000, 36_000, 48_000, 60_000]
    bid = AutoShelfBidControlManager.choose_next_test_bid(
        min_bid=12_000,
        max_bid=60_000,
        covered_bids=covered,
        min_distance=1,
    )
    assert bid == 28_000
    assert bid not in covered


def test_choose_next_test_bid_never_returns_already_covered_bid() -> None:
    covered = [12_000, 60_000]
    bid = AutoShelfBidControlManager.choose_next_test_bid(
        min_bid=12_000,
        max_bid=60_000,
        covered_bids=covered,
        min_distance=1,
    )
    assert bid == 36_000
    assert bid not in covered


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

