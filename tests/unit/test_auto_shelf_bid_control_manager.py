from __future__ import annotations

from datetime import datetime, timedelta, timezone, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    ControlReason,
    AutoShelfBidControlManager,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    BidStatsDTO,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
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


@pytest.mark.asyncio
async def test_choose_main_bid_by_strategy_uses_cycle_metric_fallback() -> None:
    """CYCLE_METRIC должен использовать старый cycle/CPC-CTR path без rec-bid."""
    analytics = MagicMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        adv_setting=MagicMock(currency="RUB"),
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    result = await manager._choose_main_bid_by_strategy(
        complex_adv=complex_adv,
        current_cycle_started_at=datetime.now(UTC),
        previous_cycle_started_at=None,
        current_main_bid_minor=20_000,
        actual_bid_minor=20_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
    )

    assert result == 25_000
    manager._choose_best_bid_with_fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_choose_main_bid_by_strategy_uses_plan_distance_best_plan_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PLAN_DISTANCE должен брать best_plan_bid из rec-bid recommendation."""
    analytics = MagicMock()
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={20_000: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.2)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader.PlanFactReader.get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=222,
                fact_predict_orders=100.0,
                fact_pay_for_order=42.0,
            )
        ),
    )
    monkeypatch.setattr(
        AutoShelfBidRecommendationReadService,
        "get_rec_bid_recommendations",
        AsyncMock(
            side_effect=lambda **kwargs: {
                "best_plan_bid": 33_000,
                "plan_ranked": [{"bid": 33_000}],
                "plan_context": kwargs["plan_context"],
            }
        ),
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            currency="RUB",
            plan_for_sales_for_day=500.0,
            target_price_for_order=100.0,
            max_price_for_order=120.0,
        ),
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    result = await manager._choose_main_bid_by_strategy(
        complex_adv=complex_adv,
        current_cycle_started_at=datetime.now(UTC),
        previous_cycle_started_at=None,
        current_main_bid_minor=20_000,
        actual_bid_minor=20_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
    )

    assert result == 33_000
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    assert (
        AutoShelfBidRecommendationReadService.get_rec_bid_recommendations.await_args.kwargs[
            "plan_context"
        ].target_order_cost
        == 120.0
    )


@pytest.mark.asyncio
async def test_choose_main_bid_by_strategy_uses_plan_distance_target_cost_when_plan_met(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PLAN_DISTANCE должен брать target_price_for_order, когда план уже выполнен."""
    analytics = MagicMock()
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={20_000: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.2)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader.PlanFactReader.get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=222,
                fact_predict_orders=500.0,
                fact_pay_for_order=42.0,
            )
        ),
    )
    monkeypatch.setattr(
        AutoShelfBidRecommendationReadService,
        "get_rec_bid_recommendations",
        AsyncMock(
            side_effect=lambda **kwargs: {
                "best_plan_bid": 33_000,
                "plan_ranked": [{"bid": 33_000}],
                "plan_context": kwargs["plan_context"],
            }
        ),
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            currency="RUB",
            plan_for_sales_for_day=500.0,
            target_price_for_order=100.0,
            max_price_for_order=120.0,
        ),
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    result = await manager._choose_main_bid_by_strategy(
        complex_adv=complex_adv,
        current_cycle_started_at=datetime.now(UTC),
        previous_cycle_started_at=None,
        current_main_bid_minor=20_000,
        actual_bid_minor=20_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
    )

    assert result == 33_000
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    assert (
        AutoShelfBidRecommendationReadService.get_rec_bid_recommendations.await_args.kwargs[
            "plan_context"
        ].target_order_cost
        == 100.0
    )


@pytest.mark.asyncio
async def test_choose_main_bid_by_strategy_plan_distance_without_recommendation_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PLAN_DISTANCE без рекомендации не должен падать в cycle fallback."""
    analytics = MagicMock()
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={20_000: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.2)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader.PlanFactReader.get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=222,
                fact_predict_orders=100.0,
                fact_pay_for_order=42.0,
            )
        ),
    )
    monkeypatch.setattr(
        AutoShelfBidRecommendationReadService,
        "get_rec_bid_recommendations",
        AsyncMock(return_value={"best_plan_bid": None, "plan_ranked": []}),
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=None,
        adv_setting=MagicMock(
            currency="RUB",
            plan_for_sales_for_day=500.0,
            target_price_for_order=100.0,
            max_price_for_order=120.0,
        ),
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    result = await manager._choose_main_bid_by_strategy(
        complex_adv=complex_adv,
        current_cycle_started_at=datetime.now(UTC),
        previous_cycle_started_at=None,
        current_main_bid_minor=20_000,
        actual_bid_minor=20_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
    )

    assert result is None
    manager._choose_best_bid_with_fallback.assert_not_awaited()


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


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, 60),
        (0, 60),
        (30, 60),
        (60, 60),
        (120, 120),
    ],
)
def test_target_observation_minutes_or_default_normalizes_minimum(
    raw_value: int | None,
    expected: int,
) -> None:
    assert AutoShelfBidControlManager._target_observation_minutes_or_default(
        raw_value
    ) == expected


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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
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
async def test_handle_main_mode_plan_distance_resets_when_selected_bid_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=16_000)  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=12),
        test_started_at=datetime.now(UTC) - timedelta(hours=12),
        main_started_at=datetime.now(UTC) - timedelta(hours=10),
        current_main_bid_minor=12_000,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=12_000,
    )

    assert state.current_main_bid_minor == 16_000
    assert state.main_started_at is not None
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    repository.save_state.assert_awaited_once()
    manager._set_target_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=16_000,
        currency=state.currency,
    )
    analytics.get_bid_stats.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_plan_distance_continues_when_selected_bid_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    manager.choose_next_test_bid = MagicMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=12),
        test_started_at=datetime.now(UTC) - timedelta(hours=12),
        main_started_at=datetime.now(UTC) - timedelta(hours=10),
        current_main_bid_minor=12_000,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            currency="RUB",
            plan_for_sales_for_day=500.0,
            target_price_for_order=100.0,
            max_price_for_order=120.0,
        ),
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=12_000,
    )

    assert state.current_mode == "test"
    assert state.current_main_bid_minor == 12_000
    repository.save_state.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_main_mode_plan_distance_waits_for_observation_minutes_before_rec_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(
        return_value={25_000: 0.1}
    )
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.2
    )
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
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader.PlanFactReader.get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=222,
                fact_predict_orders=100.0,
                fact_pay_for_order=42.0,
            )
        ),
    )
    monkeypatch.setattr(
        AutoShelfBidRecommendationReadService,
        "get_rec_bid_recommendations",
        AsyncMock(return_value={"best_plan_bid": None, "plan_ranked": []}),
    )
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=2),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=datetime.now(UTC) - timedelta(minutes=10),
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            currency="RUB",
            plan_for_sales_for_day=500.0,
            target_price_for_order=100.0,
            max_price_for_order=120.0,
        ),
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
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_plan_distance_waits_for_impressions_before_rec_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(
        return_value={25_000: 0.1}
    )
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.2
    )
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
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader.PlanFactReader.get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=222,
                fact_predict_orders=100.0,
                fact_pay_for_order=42.0,
            )
        ),
    )
    monkeypatch.setattr(
        AutoShelfBidRecommendationReadService,
        "get_rec_bid_recommendations",
        AsyncMock(return_value={"best_plan_bid": None, "plan_ranked": []}),
    )
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=12),
        test_started_at=datetime.now(UTC) - timedelta(hours=12),
        main_started_at=datetime.now(UTC) - timedelta(hours=10),
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            currency="RUB",
            plan_for_sales_for_day=500.0,
            target_price_for_order=100.0,
            max_price_for_order=120.0,
        ),
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
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_plan_distance_rec_failure_after_gates_returns_best_bid_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(
        return_value={25_000: 0.1}
    )
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.2
    )
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
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader.PlanFactReader.get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=222,
                fact_predict_orders=100.0,
                fact_pay_for_order=42.0,
            )
        ),
    )
    monkeypatch.setattr(
        AutoShelfBidRecommendationReadService,
        "get_rec_bid_recommendations",
        AsyncMock(return_value={"best_plan_bid": None, "plan_ranked": []}),
    )
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=12),
        test_started_at=datetime.now(UTC) - timedelta(hours=12),
        main_started_at=datetime.now(UTC) - timedelta(hours=10),
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            currency="RUB",
            plan_for_sales_for_day=500.0,
            target_price_for_order=100.0,
            max_price_for_order=120.0,
        ),
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

    assert state.last_reason == ControlReason.BEST_BID_NOT_FOUND
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_waits_when_main_started_at_missing() -> None:
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
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=2),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
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

    assert state.main_started_at is not None
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    repository.save_state.assert_awaited_once()
    analytics.get_impressions.assert_not_awaited()
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
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
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_uses_main_started_at_even_if_cycle_is_recent() -> None:
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
    now = datetime.now(UTC)
    main_started_at = now - timedelta(hours=10)
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=now,
        test_started_at=main_started_at,
        main_started_at=main_started_at,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
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
    analytics.get_impressions.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()
