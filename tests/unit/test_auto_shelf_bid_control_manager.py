from __future__ import annotations

from datetime import datetime, timedelta, timezone, UTC
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    ControlReason,
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_coverage_selector import (
    BidCoverage,
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


def assert_cycle_state_valid(state: object) -> None:
    current_cycle_started_at = getattr(state, "current_cycle_started_at", None)
    test_started_at = getattr(state, "test_started_at", None)
    if current_cycle_started_at and test_started_at:
        assert current_cycle_started_at <= test_started_at


def _configure_test_coverage(
    analytics: MagicMock,
    *,
    first_bucket_start: datetime,
    start_coverages: list[BidCoverage],
    now_coverages: list[BidCoverage],
) -> None:
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=first_bucket_start
    )
    analytics.get_bid_coverages = AsyncMock(
        side_effect=[start_coverages, now_coverages, now_coverages]
    )


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
        currency="RUB",
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
        currency="RUB",
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
        currency="RUB",
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
        currency="RUB",
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


@pytest.mark.parametrize(
    ("minutes", "expected_hours"),
    [
        (60, 1),
        (90, 2),
        (120, 2),
    ],
)
def test_target_observation_hours_from_minutes_uses_ceiling(
    minutes: int,
    expected_hours: int,
) -> None:
    assert AutoShelfBidControlManager._target_observation_hours_from_minutes(
        minutes
    ) == expected_hours


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
async def test_handle_test_mode_stays_in_test_when_coverage_layers_do_not_advance() -> None:
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
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=2_503,
                valid_hours=1,
            )
        ],
        now_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=2_503,
                valid_hours=1,
            )
        ],
    )
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
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
        actual_bid_minor=21_000,
    )

    assert state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME
    analytics.get_impressions.assert_not_awaited()
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
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[],
        now_coverages=[],
    )
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

    assert state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME
    repository.save_state.assert_awaited_once()
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_switches_to_main_after_closed_layers_advance() -> None:
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
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=0,
                valid_hours=0,
            )
        ],
        now_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=2_000,
                valid_hours=1,
            )
        ],
    )
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
    assert analytics.get_first_available_bid_bucket_start.await_count == 2
    assert analytics.get_bid_coverages.await_count == 2
    manager._choose_best_bid_with_fallback.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_falls_back_to_known_main_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=0,
                valid_hours=0,
            )
        ],
        now_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=2_000,
                valid_hours=1,
            )
        ],
    )
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
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        MagicMock(return_value=None),
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 25_000
    assert state.main_started_at is not None
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=25_000,
    )
    repository.save_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_continues_test_until_two_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=8_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    now = datetime(2026, 6, 11, 12, 0, 0, tzinfo=UTC)
    current_cycle_started_at = datetime(2026, 6, 11, 8, 0, 0, tzinfo=UTC)
    test_started_at = datetime(2026, 6, 11, 10, 0, 0, tzinfo=UTC)
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        start_coverages=[
            BidCoverage(
                bid_minor=8_000,
                impressions=0,
                valid_hours=0,
            )
        ],
        now_coverages=[
            BidCoverage(
                bid_minor=8_000,
                impressions=2_000,
                valid_hours=1,
            )
        ],
    )
    selector_mock = MagicMock(return_value=20_000)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    state = MagicMock(
        current_test_bid_minor=8_000,
        current_mode="test",
        current_cycle_started_at=current_cycle_started_at,
        previous_cycle_started_at=None,
        test_started_at=test_started_at,
        main_started_at=None,
        current_main_bid_minor=8_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=20_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=775965323,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager._handle_test_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=8_000,
            actual_bid_minor=8_000,
        )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 20_000
    assert state.main_started_at is None
    assert state.test_started_at == now
    assert state.current_cycle_started_at == current_cycle_started_at
    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_TEST
    assert analytics.get_first_available_bid_bucket_start.await_count == 3
    assert analytics.get_bid_coverages.await_count == 3
    selector_mock.assert_called_once()
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=20_000,
    )
    repository.save_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_allows_main_after_two_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=18_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        start_coverages=[
            BidCoverage(
                bid_minor=8_000,
                impressions=0,
                valid_hours=0,
            )
        ],
        now_coverages=[
            BidCoverage(
                bid_minor=8_000,
                impressions=2_000,
                valid_hours=1,
            ),
            BidCoverage(
                bid_minor=20_000,
                impressions=2_000,
                valid_hours=1,
            ),
        ],
    )
    selector_mock = MagicMock(return_value=12_000)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    state = MagicMock(
        current_test_bid_minor=8_000,
        current_mode="test",
        current_cycle_started_at=datetime(2026, 6, 11, 8, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=datetime(2026, 6, 11, 10, 0, 0, tzinfo=UTC),
        main_started_at=None,
        current_main_bid_minor=8_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=20_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=775965323,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=8_000,
        actual_bid_minor=8_000,
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 18_000
    assert state.main_started_at is not None
    selector_mock.assert_called_once()
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=18_000,
    )
    repository.save_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_returns_best_bid_not_found_without_main_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=0,
                valid_hours=0,
            )
        ],
        now_coverages=[
            BidCoverage(
                bid_minor=20_000,
                impressions=2_000,
                valid_hours=1,
            )
        ],
    )
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=2),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=None,
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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        MagicMock(return_value=None),
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
    )

    assert state.last_reason == ControlReason.BEST_BID_NOT_FOUND
    assert state.current_mode == "test"
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_test_mode_live_regression_keeps_test_when_layers_do_not_advance() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=2_503)
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=33_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    test_started_at = datetime.now(UTC) - timedelta(hours=1)
    current_cycle_started_at = test_started_at - timedelta(hours=2)
    first_bucket_start = datetime.now(UTC) - timedelta(hours=6)
    _configure_test_coverage(
        analytics,
        first_bucket_start=first_bucket_start,
        start_coverages=[
            BidCoverage(
                bid_minor=60_000,
                impressions=1_764,
                valid_hours=1,
            )
        ],
        now_coverages=[
            BidCoverage(
                bid_minor=60_000,
                impressions=1_764,
                valid_hours=1,
            )
        ],
    )
    state = MagicMock(
        current_test_bid_minor=60_000,
        current_mode="test",
        current_cycle_started_at=current_cycle_started_at,
        test_started_at=test_started_at,
        main_started_at=None,
        current_main_bid_minor=25_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=2_000,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=10749810,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=60_000,
    )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 60_000
    assert state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME
    assert analytics.get_first_available_bid_bucket_start.await_count == 2
    assert analytics.get_bid_coverages.await_count == 2
    assert analytics.get_first_available_bid_bucket_start.await_args_list[0].kwargs == {
        "nmid": 10749810,
        "currency": "RUB",
        "price_minor": None,
        "mode": None,
    }
    assert analytics.get_bid_coverages.await_args_list[0].kwargs["price_minor"] is None
    assert analytics.get_bid_coverages.await_args_list[0].kwargs["mode"] is None
    assert analytics.get_bid_coverages.await_args_list[0].kwargs["date_to"] == test_started_at
    assert analytics.get_bid_coverages.await_args_list[1].kwargs["date_to"] >= test_started_at
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


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
        target_test_observation_minutes=90,
        target_main_impressions=10,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    initial_cycle_started_at = state.current_cycle_started_at

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=24_000,
    )

    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    assert state.current_mode == "main"
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=25_000,
        currency=state.currency,
    )


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
        target_test_observation_minutes=90,
        target_main_impressions=10,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    initial_cycle_started_at = state.current_cycle_started_at

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=12_000,
    )

    assert state.current_main_bid_minor == 16_000
    assert state.current_mode == "main"
    assert state.main_started_at is not None
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    repository.save_state.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=16_000,
    )
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_keeps_cycle_and_test_state_when_plan_bid_changes() -> None:
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=24_000)  # type: ignore[method-assign]
    manager.choose_next_test_bid = MagicMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    t1 = datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC)
    t2 = datetime(2026, 6, 9, 7, 15, 0, tzinfo=UTC)
    now = datetime(2026, 6, 9, 8, 0, 0, tzinfo=UTC)
    state = MagicMock(
        current_test_bid_minor=45_000,
        current_mode="main",
        current_cycle_started_at=t1,
        test_started_at=t2,
        main_started_at=datetime(2026, 6, 9, 6, 0, 0, tzinfo=UTC),
        current_main_bid_minor=16_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=90,
        target_main_impressions=10,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=12_000,
            actual_bid_minor=12_000,
        )

    assert state.current_main_bid_minor == 24_000
    assert state.main_started_at == now
    assert state.current_cycle_started_at == t1
    assert state.test_started_at == t2
    assert state.current_test_bid_minor == 45_000
    assert_cycle_state_valid(state)
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=24_000,
    )


@pytest.mark.asyncio
async def test_handle_main_mode_repairs_corrupted_cycle_start_before_plan_bid_change() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=24_000)  # type: ignore[method-assign]
    manager.choose_next_test_bid = MagicMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    previous_cycle = datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC)
    test_started = datetime(2026, 6, 8, 15, 56, 56, tzinfo=UTC)
    current_cycle = datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC)
    now = datetime(2026, 6, 9, 8, 0, 0, tzinfo=UTC)
    state = MagicMock(
        current_test_bid_minor=45_000,
        current_mode="main",
        current_cycle_started_at=current_cycle,
        previous_cycle_started_at=previous_cycle,
        test_started_at=test_started,
        main_started_at=datetime(2026, 6, 9, 6, 0, 0, tzinfo=UTC),
        current_main_bid_minor=16_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=90,
        target_main_impressions=10,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=12_000,
            actual_bid_minor=12_000,
        )

    assert state.current_main_bid_minor == 24_000
    assert state.main_started_at == now
    assert state.current_cycle_started_at == previous_cycle
    assert state.test_started_at == test_started
    assert state.current_test_bid_minor == 45_000
    assert_cycle_state_valid(state)
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=24_000,
    )


@pytest.mark.asyncio
async def test_handle_main_mode_repairs_missing_previous_cycle_start_before_plan_bid_change() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=24_000)  # type: ignore[method-assign]
    manager.choose_next_test_bid = MagicMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    test_started = datetime(2026, 6, 8, 15, 56, 56, tzinfo=UTC)
    current_cycle = datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC)
    now = datetime(2026, 6, 9, 8, 0, 0, tzinfo=UTC)
    state = MagicMock(
        current_test_bid_minor=45_000,
        current_mode="main",
        current_cycle_started_at=current_cycle,
        previous_cycle_started_at=None,
        test_started_at=test_started,
        main_started_at=datetime(2026, 6, 9, 6, 0, 0, tzinfo=UTC),
        current_main_bid_minor=16_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=90,
        target_main_impressions=10,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=12_000,
            actual_bid_minor=12_000,
        )

    assert state.current_cycle_started_at == test_started
    assert state.test_started_at == test_started
    assert state.current_test_bid_minor == 45_000
    assert_cycle_state_valid(state)
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=24_000,
    )


@pytest.mark.asyncio
async def test_repair_cycle_started_at_is_idempotent_for_valid_state() -> None:
    state = MagicMock(
        current_cycle_started_at=datetime(2026, 6, 8, 10, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
        test_started_at=datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC),
        last_reason=None,
    )

    assert AutoShelfBidControlManager.repair_cycle_started_at(state) is False
    assert state.current_cycle_started_at == datetime(2026, 6, 8, 10, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_handle_main_mode_does_not_save_state_when_cycle_is_valid() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_bid_stats = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=24_000)  # type: ignore[method-assign]
    manager.choose_next_test_bid = MagicMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    test_started = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
    current_cycle = datetime(2026, 6, 8, 10, 0, 0, tzinfo=UTC)
    now = datetime(2026, 6, 9, 8, 0, 0, tzinfo=UTC)
    state = MagicMock(
        current_test_bid_minor=45_000,
        current_mode="main",
        current_cycle_started_at=current_cycle,
        previous_cycle_started_at=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
        test_started_at=test_started,
        main_started_at=datetime(2026, 6, 9, 6, 0, 0, tzinfo=UTC),
        current_main_bid_minor=16_000,
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
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=12_000,
            actual_bid_minor=12_000,
        )

    repository.save_state.assert_not_called()
    assert_cycle_state_valid(state)


@pytest.mark.asyncio
async def test_handle_main_mode_plan_distance_continues_when_selected_bid_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_first_available_bid_bucket_start = AsyncMock(return_value=None)
    analytics.get_bid_coverages = AsyncMock(return_value=[])
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
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
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
    initial_cycle_started_at = state.current_cycle_started_at

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=12_000,
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 12_000
    assert state.current_cycle_started_at == initial_cycle_started_at
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    analytics.get_first_available_bid_bucket_start.assert_awaited_once()
    analytics.get_bid_coverages.assert_not_awaited()
    selector_mock.assert_called_once()
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


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
async def test_handle_main_mode_plan_distance_uses_next_test_bid_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    )
    analytics.get_bid_coverages = AsyncMock(
        return_value=[
            BidCoverage(bid_minor=25_000, impressions=4_000, valid_hours=2),
            BidCoverage(bid_minor=33_000, impressions=0, valid_hours=0),
        ]
    )
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(
        return_value={20_500: 0.1}
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=33_000)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
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
        current_test_bid_minor=60_000,
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=12),
        main_started_at=datetime.now(UTC) - timedelta(hours=10),
        current_main_bid_minor=20_500,
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
        actual_bid_minor=20_500,
    )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 33_000
    assert state.test_started_at is not None
    assert state.current_cycle_started_at == datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    assert state.last_reason == ControlReason.MAIN_COMPLETED_SWITCH_TO_TEST
    analytics.get_first_available_bid_bucket_start.assert_awaited_once_with(
        nmid=111,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    analytics.get_bid_coverages.assert_awaited_once_with(
        nmid=111,
        date_from=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        date_to=ANY,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    selector_mock.assert_called_once()
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once_with(
        complex_adv,
        state=state,
        bid_minor=33_000,
    )
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_plan_distance_continues_safe_main_when_no_next_test_bid_and_no_best_plan_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_first_available_bid_bucket_start = AsyncMock(return_value=None)
    analytics.get_bid_coverages = AsyncMock(return_value=[])
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
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
        current_cycle_started_at=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
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

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 25_000
    assert state.main_started_at is not None
    assert state.current_cycle_started_at == datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    analytics.get_first_available_bid_bucket_start.assert_awaited_once_with(
        nmid=111,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    analytics.get_bid_coverages.assert_not_awaited()
    selector_mock.assert_called_once()
    manager._choose_main_bid_by_strategy.assert_called_once()
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_plan_distance_keeps_main_bid_and_restarts_window_when_selected_bid_same(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_first_available_bid_bucket_start = AsyncMock(return_value=None)
    analytics.get_bid_coverages = AsyncMock(return_value=[])
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
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
    now = datetime.now(UTC)
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=now - timedelta(hours=12),
        test_started_at=now - timedelta(hours=12),
        main_started_at=now - timedelta(hours=10),
        current_main_bid_minor=25_000,
        currency="RUB",
        last_reason=ControlReason.MAIN_WAITING_OBSERVATION_TIME,
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

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 25_000
    assert state.main_started_at is not None
    assert state.current_cycle_started_at is not None
    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    analytics.get_first_available_bid_bucket_start.assert_awaited_once_with(
        nmid=111,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    analytics.get_bid_coverages.assert_not_awaited()
    selector_mock.assert_called_once()
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


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
