from __future__ import annotations

from datetime import datetime, timedelta, timezone, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    ControlReason,
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
        cycle_started_at=datetime.now(UTC),
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


def test_calc_target_main_observation_minutes_with_valid_share() -> None:
    target = AutoShelfBidControlManager._calc_target_main_observation_minutes(60, 0.1)
    assert target == 540


def test_calc_target_main_observation_minutes_invalid_share_returns_none() -> None:
    assert AutoShelfBidControlManager._calc_target_main_observation_minutes(60, 0) is None
    assert AutoShelfBidControlManager._calc_target_main_observation_minutes(60, 0.5) is None


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


@pytest.mark.asyncio
async def test_handle_test_mode_waits_for_observation_minutes_even_if_impressions_enough() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=1_000)
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC),
        main_started_at=None,
        current_main_bid_minor=25_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
    )

    assert state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_accepts_nullable_target_observation_minutes() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=0)
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=2),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=25_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=1_000,
        target_test_observation_minutes=None,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
    )

    assert state.last_reason == ControlReason.TEST_WAITING_IMPRESSIONS
    repository.save_state.assert_awaited_once()
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_switches_to_main_after_time_and_impressions() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=1_000)
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=33_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    old_started_at = datetime.now(UTC) - timedelta(hours=2)
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="test",
        current_cycle_started_at=old_started_at,
        test_started_at=old_started_at,
        main_started_at=None,
        current_main_bid_minor=25_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=25_000,
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 33_000
    manager._choose_best_bid_with_fallback.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_main_mode_waits_for_observation_minutes() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC),
        main_started_at=datetime.now(UTC),
        current_main_bid_minor=25_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        target_main_impressions=10,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=25_000,
    )

    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_accepts_nullable_target_observation_minutes() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=2),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=datetime.now(UTC) - timedelta(hours=2),
        current_main_bid_minor=25_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=1_000,
        target_test_observation_minutes=None,
        target_main_impressions=1_000,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=25_000,
    )

    assert state.last_reason == ControlReason.MAIN_WAITING_IMPRESSIONS
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()
