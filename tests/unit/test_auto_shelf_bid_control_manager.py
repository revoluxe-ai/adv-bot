from __future__ import annotations

from datetime import datetime, timedelta, timezone, UTC
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from typing import Any, cast

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    ControlReason,
    AutoShelfBidControlManager,
    MainBidRefreshResult,
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
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.decision_snapshot_dto import (
    AutoShelfBidControlDecisionSnapshot,
    BidSyncStatus,
    resolve_bid_sync_status,
    resolve_expected_bid_minor,
    snapshot_can_count_progress,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.decision import (
    coverage_date_from_for_epoch,
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


def _configure_plan_distance_test_transition(
    *,
    min_bid_minor: int,
    max_bid_minor: int,
    current_test_bid_minor: int,
    covered_anchor_count: int,
    next_test_bid: int | None,
    current_main_bid_minor: int = 18_000,
) -> tuple[
    AutoShelfBidControlManager,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    """Подготовить PLAN_DISTANCE test-mode сценарий с управляемым snapshot."""
    analytics = MagicMock()
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=current_main_bid_minor)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._closed_layers_for_bid_at = AsyncMock(side_effect=[0, 1])  # type: ignore[method-assign]
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    manager._analytics.get_bid_stats = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            BidStatsDTO(
                bid_minor=current_test_bid_minor,
                currency="RUB",
                mode=None,
                last_interval_at=None,
                impressions=500,
                clicks=20,
                carts=2,
                orders=1,
                spend=100.0,
                cart_cpa=5.0,
                ctr=0.04,
                cart_cr=0.1,
            ),
            BidStatsDTO(
                bid_minor=current_main_bid_minor,
                currency="RUB",
                mode=None,
                last_interval_at=None,
                impressions=500,
                clicks=15,
                carts=1,
                orders=0,
                spend=90.0,
                cart_cpa=6.0,
                ctr=0.03,
                cart_cr=0.05,
            ),
        ]
    )
    manager._build_coverage_snapshot = AsyncMock(
        return_value=([], 0, covered_anchor_count, next_test_bid)
    )  # type: ignore[method-assign]
    # nmid must match complex_adv.main_nmid; shelf-exhausted fields must be
    # real bools/None so MagicMock truthiness does not fake an active our-block.
    state = MagicMock(
        nmid=775965323,
        current_test_bid_minor=current_test_bid_minor,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC) - timedelta(hours=2),
        previous_cycle_started_at=None,
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=12_000,
        currency="RUB",
        last_reason=None,
        shelf_exhausted_pause_active=False,
        shelf_exhausted_due_at=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=max_bid_minor,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=775965323,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    return manager, repository, state, settings_obj, complex_adv


def _snapshot_from_reconcile_state(
    state: Any,
    *,
    actual_bid_minor: int | None,
    min_bid_minor: int = 12_000,
    max_bid_minor: int = 50_000,
) -> AutoShelfBidControlDecisionSnapshot:
    fresh_main = getattr(state, "current_main_bid_minor", None)
    fresh_test = getattr(state, "current_test_bid_minor", None)
    expected = resolve_expected_bid_minor(
        current_mode=state.current_mode,
        fresh_best_main_bid_minor=fresh_main,
        fresh_next_test_bid_minor=fresh_test,
        control_enabled=True,
    )
    if expected is not None:
        expected = AutoShelfBidControlManager._clamp_bid_minor(
            int(expected),
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
        )
    status = resolve_bid_sync_status(actual_bid_minor, expected)
    return AutoShelfBidControlDecisionSnapshot(
        nmid=30369094,
        auto_adv_id=35018182,
        current_mode=state.current_mode,
        actual_bid_minor=actual_bid_minor,
        min_bid_minor=min_bid_minor,
        max_bid_minor=max_bid_minor,
        fresh_best_main_bid_minor=fresh_main,
        fresh_next_test_bid_minor=fresh_test,
        expected_bid_minor=expected,
        bid_sync_status=status,
        can_count_progress=snapshot_can_count_progress(
            expected_bid_minor=expected,
            actual_bid_minor=actual_bid_minor,
            bid_sync_status=status,
        ),
        computed_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )


def _synced_progress_snapshot(
    *,
    mode: str,
    actual_bid_minor: int,
    expected_bid_minor: int,
    nmid: int = 111,
    auto_adv_id: int = 222,
    fresh_next_test_bid_minor: int | None = None,
    fresh_best_main_bid_minor: int | None = None,
) -> AutoShelfBidControlDecisionSnapshot:
    """Synced snapshot для progress-path тестов observation waiting."""
    if fresh_next_test_bid_minor is None:
        fresh_next_test_bid_minor = (
            expected_bid_minor if mode == "test" else None
        )
    if fresh_best_main_bid_minor is None:
        fresh_best_main_bid_minor = (
            expected_bid_minor if mode == "main" else None
        )
    bid_sync_status = BidSyncStatus.SYNCED
    return AutoShelfBidControlDecisionSnapshot(
        nmid=nmid,
        auto_adv_id=auto_adv_id,
        current_mode=mode,
        actual_bid_minor=actual_bid_minor,
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        fresh_best_main_bid_minor=fresh_best_main_bid_minor,
        fresh_next_test_bid_minor=fresh_next_test_bid_minor,
        expected_bid_minor=expected_bid_minor,
        bid_sync_status=bid_sync_status,
        can_count_progress=snapshot_can_count_progress(
            expected_bid_minor=expected_bid_minor,
            actual_bid_minor=actual_bid_minor,
            bid_sync_status=bid_sync_status,
        ),
        qualified_tested_bids_count=2,
        computed_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )


def _qualified_main_worker_snapshot(
    *,
    mode: str,
    actual_bid_minor: int,
    fresh_main_bid_minor: int,
    fresh_next_test_bid_minor: int | None = None,
    qualified_tested_bids_count: int = 2,
    nmid: int = 111,
    auto_adv_id: int = 222,
    min_bid_minor: int = 12_000,
    max_bid_minor: int = 50_000,
) -> AutoShelfBidControlDecisionSnapshot:
    """Worker snapshot с qualified tested bids для main-path."""
    if fresh_next_test_bid_minor is None:
        fresh_next_test_bid_minor = actual_bid_minor if mode == "test" else None
    expected_bid_minor = resolve_expected_bid_minor(
        current_mode=mode,
        fresh_best_main_bid_minor=fresh_main_bid_minor,
        fresh_next_test_bid_minor=fresh_next_test_bid_minor,
        control_enabled=True,
    )
    bid_sync_status = resolve_bid_sync_status(actual_bid_minor, expected_bid_minor)
    return AutoShelfBidControlDecisionSnapshot(
        nmid=nmid,
        auto_adv_id=auto_adv_id,
        current_mode=mode,
        actual_bid_minor=actual_bid_minor,
        min_bid_minor=min_bid_minor,
        max_bid_minor=max_bid_minor,
        fresh_best_main_bid_minor=fresh_main_bid_minor,
        fresh_next_test_bid_minor=fresh_next_test_bid_minor,
        expected_bid_minor=expected_bid_minor,
        bid_sync_status=bid_sync_status,
        can_count_progress=snapshot_can_count_progress(
            expected_bid_minor=expected_bid_minor,
            actual_bid_minor=actual_bid_minor,
            bid_sync_status=bid_sync_status,
        ),
        qualified_tested_bids_count=qualified_tested_bids_count,
        computed_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )


def _build_reconcile_fixture(
    *,
    current_mode: str,
    current_test_bid_minor: int | None,
    current_main_bid_minor: int | None,
    actual_bid_minor: int | None,
) -> tuple[
    AutoShelfBidControlManager,
    MagicMock,
    MagicMock,
    Any,
    Any,
    Any,
]:
    """Подготовить manager/update fixture для проверки reconcile-пути."""
    repository = MagicMock()
    repository.get_settings = AsyncMock()
    repository.repair_settings_units = AsyncMock()
    repository.get_state = AsyncMock()
    repository.save_state = AsyncMock()
    repository.update_state_reason = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    # update() → _apply_shelf_exhausted_tick awaits get_bid_stats when
    # current_cycle_started_at is set; MagicMock is not awaitable.
    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=analytics,
    )
    manager._get_actual_bid = AsyncMock(return_value=actual_bid_minor)  # type: ignore[method-assign]
    manager._resolve_min_bid_minor = MagicMock(return_value=12_000)  # type: ignore[method-assign]
    manager._is_eligible = MagicMock(return_value=(True, ControlReason.SETTINGS_UPDATED))  # type: ignore[method-assign]
    manager._handle_test_mode = AsyncMock()  # type: ignore[method-assign]
    manager._handle_main_mode = AsyncMock()  # type: ignore[method-assign]
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    # nmid must match complex_adv.main_nmid; shelf-exhausted fields must be
    # explicit so update() → _apply_shelf_exhausted_tick does not see MagicMock
    # truthiness or missing attrs as an active our-block.
    state = SimpleNamespace(
        nmid=30369094,
        current_mode=current_mode,
        current_test_bid_minor=current_test_bid_minor,
        current_main_bid_minor=current_main_bid_minor,
        current_cycle_started_at=datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 6, 11, 12, 0, 0, tzinfo=UTC),
        test_started_at=datetime(2026, 6, 12, 13, 0, 0, tzinfo=UTC),
        main_started_at=datetime(2026, 6, 12, 14, 0, 0, tzinfo=UTC),
        currency="RUB",
        last_reason=None,
        shelf_exhausted_pause_active=False,
        shelf_exhausted_due_at=None,
        shelf_exhausted_epoch_start=None,
    )
    settings_obj = SimpleNamespace(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
    )
    complex_adv = SimpleNamespace(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    repository.get_settings.return_value = settings_obj
    repository.repair_settings_units.return_value = settings_obj
    repository.get_state.return_value = state

    async def _build_snapshot(*_args: object, **_kwargs: object) -> AutoShelfBidControlDecisionSnapshot:
        return _snapshot_from_reconcile_state(
            state,
            actual_bid_minor=actual_bid_minor,
            min_bid_minor=12_000,
            max_bid_minor=int(settings_obj.max_bid_minor),
        )

    async def _apply_sync(
        complex_adv: object,
        *,
        state: object,
        snapshot: AutoShelfBidControlDecisionSnapshot,
        min_bid_minor: int,
        max_bid_minor: int,
        now: datetime,
        **_kwargs: object,
    ) -> bool:
        return await manager._reconcile_expected_bid_for_current_mode(
            complex_adv,  # type: ignore[arg-type]
            state=state,  # type: ignore[arg-type]
            actual_bid_minor=snapshot.actual_bid_minor,
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
            now=now,
            expected_bid_minor=snapshot.expected_bid_minor,
        )

    manager.build_decision_snapshot = AsyncMock(side_effect=_build_snapshot)  # type: ignore[method-assign]
    manager.apply_bid_sync_from_snapshot = AsyncMock(side_effect=_apply_sync)  # type: ignore[method-assign]
    return manager, repository, wb_bid_setter, state, settings_obj, complex_adv


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
async def test_choose_main_bid_by_strategy_uses_plan_distance_plan_ranked_top(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PLAN_DISTANCE должен брать plan_ranked[0], а не CPO-capped best_plan_bid."""
    analytics = MagicMock()
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={20_000: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.2)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        analytics_repository=analytics,
    )
    manager._choose_best_bid_with_fallback = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._fetch_plan_distance_rec_result = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "view": {
                "best_plan_bid": 20_000,
                "plan_ranked": [{"bid": 33_000}],
            },
            "best_plan_bid": 20_000,
        }
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
        original_max_cpo=120.0,
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
    manager._fetch_plan_distance_rec_result.assert_awaited_once()


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
        original_max_cpo=120.0,
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
        max_bid_minor=70_000,
    )

    assert result == 33_000
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    plan_context = (
        AutoShelfBidRecommendationReadService.get_rec_bid_recommendations.await_args.kwargs[
            "plan_context"
        ]
    )
    assert plan_context.target_order_cost == 100.0
    assert plan_context.max_order_cost == 120.0


@pytest.mark.asyncio
async def test_choose_main_bid_by_strategy_plan_distance_uses_original_max_cpo_for_max_order_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PLAN_DISTANCE должен брать max_order_cost из ComplexAdv.original_max_cpo."""
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
        original_max_cpo=250.0,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._choose_main_bid_by_strategy(
        complex_adv=complex_adv,
        currency="RUB",
        current_cycle_started_at=datetime.now(UTC),
        previous_cycle_started_at=None,
        current_main_bid_minor=20_000,
        actual_bid_minor=20_000,
        min_bid_minor=12_000,
        max_bid_minor=70_000,
    )

    plan_context = (
        AutoShelfBidRecommendationReadService.get_rec_bid_recommendations.await_args.kwargs[
            "plan_context"
        ]
    )
    assert plan_context.target_order_cost == 120.0
    assert plan_context.max_order_cost == 250.0


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
        max_bid_minor=70_000,
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


def test_middle_bid_snaps_to_whole_rubles_preferring_lower_on_tie() -> None:
    bid = AutoShelfBidControlManager._middle_bid(14_100, 22_200)
    assert bid == 18_100


def test_choose_next_test_bid_snaps_gap_midpoint_to_whole_rubles() -> None:
    bid = AutoShelfBidControlManager.choose_next_test_bid(
        min_bid=14_100,
        max_bid=22_200,
        covered_bids=[14_100, 22_200],
        min_distance=1,
    )
    assert bid == 18_100


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
async def test_update_reconciles_test_mode_bid_before_test_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, repository, wb_bid_setter, state, _, complex_adv = _build_reconcile_fixture(
        current_mode="test",
        current_test_bid_minor=26_200,
        current_main_bid_minor=14_000,
        actual_bid_minor=14_000,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC)):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=26_200,
        currency="RUB",
    )
    manager._handle_test_mode.assert_not_awaited()
    manager._handle_main_mode.assert_not_awaited()
    repository.save_state.assert_awaited_once()
    assert state.current_mode == "test"
    assert state.test_started_at == datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC)
    assert state.current_cycle_started_at == datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)
    assert state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME


@pytest.mark.asyncio
async def test_update_reconciles_main_mode_bid_before_main_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, repository, wb_bid_setter, state, _, complex_adv = _build_reconcile_fixture(
        current_mode="main",
        current_test_bid_minor=26_200,
        current_main_bid_minor=14_000,
        actual_bid_minor=26_200,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=datetime(2026, 6, 13, 12, 10, 0, tzinfo=UTC)):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once()
    assert wb_bid_setter.set_bid.await_args.kwargs["bid_minor"] == 14_000
    manager._handle_test_mode.assert_not_awaited()
    manager._handle_main_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_skips_reconcile_when_test_bid_matches_and_runs_normal_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, repository, wb_bid_setter, state, _, complex_adv = _build_reconcile_fixture(
        current_mode="test",
        current_test_bid_minor=26_200,
        current_main_bid_minor=14_000,
        actual_bid_minor=26_200,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=datetime(2026, 6, 13, 12, 15, 0, tzinfo=UTC)):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_not_awaited()
    manager._handle_test_mode.assert_awaited_once()
    manager._handle_main_mode.assert_not_awaited()
    repository.save_state.assert_not_awaited()
    assert state.current_cycle_started_at == datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_update_skips_reconcile_when_main_bid_matches_and_runs_normal_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, repository, wb_bid_setter, state, _, complex_adv = _build_reconcile_fixture(
        current_mode="main",
        current_test_bid_minor=26_200,
        current_main_bid_minor=14_000,
        actual_bid_minor=14_000,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=datetime(2026, 6, 13, 12, 20, 0, tzinfo=UTC)):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_not_awaited()
    manager._handle_test_mode.assert_not_awaited()
    manager._handle_main_mode.assert_awaited_once()
    repository.save_state.assert_not_awaited()
    assert state.current_cycle_started_at == datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_reconcile_expected_bid_returns_false_when_expected_bid_missing() -> None:
    manager, repository, wb_bid_setter, state, _, complex_adv = _build_reconcile_fixture(
        current_mode="test",
        current_test_bid_minor=None,
        current_main_bid_minor=None,
        actual_bid_minor=14_000,
    )

    result = await manager._reconcile_expected_bid_for_current_mode(
        complex_adv,
        state=state,
        actual_bid_minor=14_000,
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        now=datetime(2026, 6, 13, 12, 25, 0, tzinfo=UTC),
        expected_bid_minor=None,
    )

    assert result is False
    wb_bid_setter.set_bid.assert_not_awaited()
    repository.save_state.assert_not_awaited()
    assert state.current_cycle_started_at == datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_update_reconciles_main_mode_clamps_bid_above_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, repository, wb_bid_setter, state, settings_obj, complex_adv = _build_reconcile_fixture(
        current_mode="main",
        current_test_bid_minor=26_200,
        current_main_bid_minor=60_000,
        actual_bid_minor=14_000,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=datetime(2026, 6, 13, 12, 30, 0, tzinfo=UTC)):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once()
    assert wb_bid_setter.set_bid.await_args.kwargs["bid_minor"] == 50_000
    manager._handle_test_mode.assert_not_awaited()
    manager._handle_main_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_reconciles_main_mode_clamps_bid_below_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, repository, wb_bid_setter, state, settings_obj, complex_adv = _build_reconcile_fixture(
        current_mode="main",
        current_test_bid_minor=26_200,
        current_main_bid_minor=8_000,
        actual_bid_minor=14_000,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=datetime(2026, 6, 13, 12, 35, 0, tzinfo=UTC)):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once()
    assert wb_bid_setter.set_bid.await_args.kwargs["bid_minor"] == 12_000
    manager._handle_test_mode.assert_not_awaited()
    manager._handle_main_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_reconciles_test_mode_clamps_bid_outside_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, repository, wb_bid_setter, state, settings_obj, complex_adv = _build_reconcile_fixture(
        current_mode="test",
        current_test_bid_minor=60_000,
        current_main_bid_minor=14_000,
        actual_bid_minor=14_000,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=datetime(2026, 6, 13, 12, 40, 0, tzinfo=UTC)):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=50_000,
        currency="RUB",
    )
    assert state.current_test_bid_minor == 50_000
    assert state.test_started_at == datetime(2026, 6, 13, 12, 40, 0, tzinfo=UTC)
    assert state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME


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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
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
        max_bid_minor=70_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="test",
        actual_bid_minor=20_000,
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        fresh_best_main_bid_minor=25_000,
        fresh_next_test_bid_minor=20_000,
        expected_bid_minor=20_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        computed_at=datetime.now(UTC),
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
        snapshot=snapshot,
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
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = _synced_progress_snapshot(
        mode="test",
        actual_bid_minor=20_000,
        expected_bid_minor=20_000,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
        snapshot=snapshot,
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
        snapshot=_qualified_main_worker_snapshot(
            mode="test",
            actual_bid_minor=25_000,
            fresh_main_bid_minor=33_000,
            fresh_next_test_bid_minor=20_000,
        ),
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 33_000
    assert analytics.get_first_available_bid_bucket_start.await_count == 2
    assert analytics.get_bid_coverages.await_count == 2
    manager._choose_best_bid_with_fallback.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


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

    assert state.current_mode == "test"
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    repository.save_state.assert_awaited()


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
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_single_bid_universe_goes_to_main() -> None:
    manager, repository, state, settings_obj, complex_adv = _configure_plan_distance_test_transition(
        min_bid_minor=8_000,
        max_bid_minor=8_000,
        current_test_bid_minor=8_000,
        covered_anchor_count=0,
        next_test_bid=8_000,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=8_000,
        actual_bid_minor=8_000,
        snapshot=_qualified_main_worker_snapshot(
            mode="test",
            actual_bid_minor=8_000,
            fresh_main_bid_minor=18_000,
            fresh_next_test_bid_minor=8_000,
            min_bid_minor=8_000,
            max_bid_minor=20_000,
        ),
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 18_000
    assert state.main_started_at is not None
    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_MAIN
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_keeps_testing_with_single_anchor_on_multi_bid_universe() -> None:
    manager, repository, state, settings_obj, complex_adv = _configure_plan_distance_test_transition(
        min_bid_minor=8_000,
        max_bid_minor=20_000,
        current_test_bid_minor=8_000,
        covered_anchor_count=1,
        next_test_bid=20_000,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=8_000,
        actual_bid_minor=8_000,
        snapshot=_qualified_main_worker_snapshot(
            mode="test",
            actual_bid_minor=8_000,
            fresh_main_bid_minor=18_000,
            fresh_next_test_bid_minor=8_000,
            min_bid_minor=8_000,
            max_bid_minor=20_000,
        ),
    )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 20_000
    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_TEST
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_switches_to_main_when_two_anchors_exist() -> None:
    manager, repository, state, settings_obj, complex_adv = _configure_plan_distance_test_transition(
        min_bid_minor=8_000,
        max_bid_minor=20_000,
        current_test_bid_minor=8_000,
        covered_anchor_count=2,
        next_test_bid=20_000,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=8_000,
        actual_bid_minor=8_000,
        snapshot=_qualified_main_worker_snapshot(
            mode="test",
            actual_bid_minor=8_000,
            fresh_main_bid_minor=18_000,
            fresh_next_test_bid_minor=8_000,
            min_bid_minor=8_000,
            max_bid_minor=20_000,
        ),
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 18_000
    assert state.main_started_at is not None
    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_MAIN
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_plan_distance_allows_main_when_next_test_bid_matches_current() -> None:
    manager, repository, state, settings_obj, complex_adv = _configure_plan_distance_test_transition(
        min_bid_minor=8_000,
        max_bid_minor=20_000,
        current_test_bid_minor=8_000,
        covered_anchor_count=1,
        next_test_bid=8_000,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=8_000,
        actual_bid_minor=8_000,
        snapshot=_qualified_main_worker_snapshot(
            mode="test",
            actual_bid_minor=8_000,
            fresh_main_bid_minor=18_000,
            fresh_next_test_bid_minor=8_000,
            min_bid_minor=8_000,
            max_bid_minor=20_000,
        ),
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 18_000
    assert state.main_started_at is not None
    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_MAIN
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


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
        snapshot=_qualified_main_worker_snapshot(
            mode="test",
            actual_bid_minor=8_000,
            fresh_main_bid_minor=18_000,
            fresh_next_test_bid_minor=8_000,
            min_bid_minor=8_000,
            max_bid_minor=20_000,
        ),
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 18_000
    assert state.main_started_at is not None
    selector_mock.assert_called_once()
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


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

    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    assert state.current_mode == "test"
    manager._choose_main_bid_by_strategy.assert_not_awaited()
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
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = _synced_progress_snapshot(
        mode="test",
        actual_bid_minor=60_000,
        expected_bid_minor=60_000,
        nmid=10749810,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=60_000,
        snapshot=snapshot,
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
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
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = _synced_progress_snapshot(
        mode="main",
        actual_bid_minor=25_000,
        expected_bid_minor=25_000,
        fresh_best_main_bid_minor=25_000,
    )
    initial_cycle_started_at = state.current_cycle_started_at

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=25_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    assert state.current_mode == "main"
    repository.save_state.assert_awaited_once()
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
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=12_000,
            expected_bid_minor=16_000,
            fresh_best_main_bid_minor=16_000,
        ),
    )

    assert state.current_main_bid_minor == 16_000
    assert state.current_mode == "main"
    assert state.main_started_at is not None
    assert state.last_reason != ControlReason.MAIN_BID_REFRESHED
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
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
            snapshot=_synced_progress_snapshot(
                mode="main",
                actual_bid_minor=12_000,
                expected_bid_minor=24_000,
                fresh_best_main_bid_minor=24_000,
            ),
        )

    assert state.current_main_bid_minor == 24_000
    assert state.current_cycle_started_at == t1
    assert state.test_started_at == t2
    assert state.current_test_bid_minor == 45_000
    assert state.last_reason != ControlReason.MAIN_BID_REFRESHED
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    assert_cycle_state_valid(state)
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


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
            snapshot=_synced_progress_snapshot(
                mode="main",
                actual_bid_minor=12_000,
                expected_bid_minor=24_000,
                fresh_best_main_bid_minor=24_000,
            ),
        )

    assert state.current_main_bid_minor == 24_000
    assert state.current_cycle_started_at == previous_cycle
    assert state.test_started_at == test_started
    assert state.current_test_bid_minor == 45_000
    assert_cycle_state_valid(state)
    assert state.last_reason != ControlReason.MAIN_BID_REFRESHED
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


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
            snapshot=_synced_progress_snapshot(
                mode="main",
                actual_bid_minor=12_000,
                expected_bid_minor=24_000,
                fresh_best_main_bid_minor=24_000,
            ),
        )

    assert state.current_cycle_started_at == test_started
    assert state.test_started_at == test_started
    assert state.current_test_bid_minor == 45_000
    assert_cycle_state_valid(state)
    repository.save_state.assert_awaited()
    assert state.last_reason != ControlReason.MAIN_BID_REFRESHED
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()




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
        max_bid_minor=70_000,
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
            snapshot=_synced_progress_snapshot(
                mode="main",
                actual_bid_minor=12_000,
                expected_bid_minor=24_000,
                fresh_best_main_bid_minor=24_000,
            ),
        )

    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
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
        max_bid_minor=70_000,
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
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=12_000,
            expected_bid_minor=12_000,
        ),
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
        auto_shelf_bid_control_enabled=True,
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
    snapshot = _synced_progress_snapshot(
        mode="main",
        actual_bid_minor=25_000,
        expected_bid_minor=25_000,
        fresh_best_main_bid_minor=25_000,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=25_000,
        snapshot=snapshot,
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
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=25_000,
            expected_bid_minor=25_000,
        ),
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
    first_bucket_start = datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    state = MagicMock(
        current_test_bid_minor=60_000,
        current_mode="main",
        current_cycle_started_at=first_bucket_start,
        test_started_at=datetime.now(UTC) - timedelta(hours=12),
        main_started_at=datetime.now(UTC) - timedelta(hours=10),
        current_main_bid_minor=20_500,
        currency="RUB",
        last_reason=None,
        shelf_exhausted_epoch_start=None,
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
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=20_500,
            expected_bid_minor=20_500,
            fresh_best_main_bid_minor=20_500,
            fresh_next_test_bid_minor=33_000,
        ),
    )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 33_000
    assert state.test_started_at is not None
    assert state.current_cycle_started_at == first_bucket_start
    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_TEST
    analytics.get_first_available_bid_bucket_start.assert_awaited_once_with(
        nmid=111,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    coverages_kwargs = analytics.get_bid_coverages.await_args.kwargs
    date_to = coverages_kwargs["date_to"]
    # ASEP: date_from = max(first_bucket, coverage_date_from_for_epoch(...));
    # epoch absent → now-7d floor (OpenSpec window clamp).
    expected_date_from = max(
        first_bucket_start,
        coverage_date_from_for_epoch(now=date_to, epoch_start=None),
    )
    analytics.get_bid_coverages.assert_awaited_once_with(
        nmid=111,
        date_from=expected_date_from,
        date_to=date_to,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    selector_mock.assert_called_once()
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
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
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=25_000,
            expected_bid_minor=25_000,
        ),
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
    manager._choose_main_bid_by_strategy.assert_not_awaited()
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
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=25_000,
            expected_bid_minor=25_000,
        ),
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
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_main_mode_cycle_metric_stops_with_best_bid_not_found_when_no_next_test_bid(
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=25_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    now = datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC)
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        test_started_at=now - timedelta(hours=12),
        main_started_at=now - timedelta(hours=10),
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
        snapshot=AutoShelfBidControlDecisionSnapshot(
            nmid=111,
            auto_adv_id=222,
            current_mode="main",
            actual_bid_minor=25_000,
            min_bid_minor=12_000,
            max_bid_minor=50_000,
            fresh_best_main_bid_minor=None,
            fresh_next_test_bid_minor=None,
            expected_bid_minor=25_000,
            bid_sync_status=BidSyncStatus.SYNCED,
            can_count_progress=True,
            qualified_tested_bids_count=0,
            computed_at=now,
        ),
    )

    assert state.current_mode == "test"
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    assert state.main_started_at is None
    assert state.current_cycle_started_at == datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    selector_mock.assert_not_called()
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_cycle_metric_main_finished_insufficient_qualified_revert_resets_test_started_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CYCLE_METRIC main finished + <2 qualified: test segment re-init with fresh test_started_at."""
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    )
    analytics.get_bid_coverages = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._maybe_continue_main_exploration = AsyncMock(return_value=(False, None))  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    now = datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC)
    old_test_started = now - timedelta(hours=12)
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        test_started_at=old_test_started,
        main_started_at=now - timedelta(hours=10),
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
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="main",
        actual_bid_minor=25_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        fresh_best_main_bid_minor=25_000,
        fresh_next_test_bid_minor=None,
        expected_bid_minor=25_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        qualified_tested_bids_count=1,
        computed_at=now,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=12_000,
            actual_bid_minor=25_000,
            snapshot=snapshot,
        )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 20_000
    assert state.test_started_at == now
    assert state.test_started_at != old_test_started
    assert state.main_started_at is None
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    assert state.last_reason != ControlReason.MAIN_WAITING_OBSERVATION_TIME
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_cycle_metric_main_finished_insufficient_qualified_no_test_bid_blocks_without_test_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CYCLE_METRIC main finished + <2 qualified + no test bid: block без test switch."""
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    )
    analytics.get_bid_coverages = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._maybe_continue_main_exploration = AsyncMock(return_value=(False, None))  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    now = datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC)
    state = MagicMock(
        current_test_bid_minor=None,
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        test_started_at=now - timedelta(hours=12),
        main_started_at=now - timedelta(hours=10),
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
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="main",
        actual_bid_minor=25_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        fresh_best_main_bid_minor=25_000,
        fresh_next_test_bid_minor=None,
        expected_bid_minor=25_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        qualified_tested_bids_count=1,
        computed_at=now,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=12_000,
            actual_bid_minor=25_000,
            snapshot=snapshot,
        )

    assert state.current_mode == "main"
    assert state.current_test_bid_minor is None
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    assert state.last_reason != ControlReason.MAIN_WAITING_OBSERVATION_TIME
    repository.save_state.assert_awaited_once()
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
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = _synced_progress_snapshot(
        mode="main",
        actual_bid_minor=25_000,
        expected_bid_minor=25_000,
        fresh_best_main_bid_minor=25_000,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=25_000,
        snapshot=snapshot,
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
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = _synced_progress_snapshot(
        mode="main",
        actual_bid_minor=25_000,
        expected_bid_minor=25_000,
        fresh_best_main_bid_minor=25_000,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=25_000,
        snapshot=snapshot,
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
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=25_000,
            expected_bid_minor=25_000,
        ),
    )

    assert state.last_reason == ControlReason.MAIN_WAITING_IMPRESSIONS
    analytics.get_impressions.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_main_bid_refresh_if_needed_applies_refresh_and_updates_state() -> None:
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=60_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    now = datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC)
    state = SimpleNamespace(
        current_mode="main",
        current_main_bid_minor=20_500,
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=None,
        main_started_at=None,
        currency="RUB",
        last_reason="manual_force_main",
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )

    result = await manager.apply_main_bid_refresh_if_needed(
        complex_adv,
        state=cast(Any, state),
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        actual_bid_minor=20_500,
        now=now,
    )

    assert result == MainBidRefreshResult.APPLIED
    assert state.current_main_bid_minor == 60_000
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_main_bid_refresh_if_needed_returns_no_change_when_target_same() -> None:
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=20_500)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = SimpleNamespace(
        current_mode="main",
        current_main_bid_minor=20_500,
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=None,
        main_started_at=datetime(2026, 6, 15, 11, 0, 0, tzinfo=UTC),
        currency="RUB",
        last_reason=None,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )

    result = await manager.apply_main_bid_refresh_if_needed(
        complex_adv,
        state=cast(Any, state),
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        actual_bid_minor=20_500,
        now=datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC),
    )

    assert result == MainBidRefreshResult.NO_CHANGE
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_main_bid_refresh_if_needed_clamps_desired_bid() -> None:
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=99_999)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = SimpleNamespace(
        current_mode="main",
        current_main_bid_minor=20_500,
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=None,
        main_started_at=None,
        currency="RUB",
        last_reason=None,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )

    result = await manager.apply_main_bid_refresh_if_needed(
        complex_adv,
        state=cast(Any, state),
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        actual_bid_minor=20_500,
        now=datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC),
    )

    assert result == MainBidRefreshResult.APPLIED
    assert state.current_main_bid_minor == 50_000
    manager._choose_main_bid_by_strategy.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_mode", "enabled", "expected_result"),
    [
        ("test", True, MainBidRefreshResult.SKIPPED_NOT_MAIN),
        ("main", False, MainBidRefreshResult.SKIPPED_DISABLED),
    ],
)
async def test_apply_main_bid_refresh_if_needed_skips_non_applicable_states(
    current_mode: str,
    enabled: bool,
    expected_result: MainBidRefreshResult,
) -> None:
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=60_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = SimpleNamespace(
        current_mode=current_mode,
        current_main_bid_minor=20_500,
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=None,
        main_started_at=None,
        currency="RUB",
        last_reason=None,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=enabled,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )

    result = await manager.apply_main_bid_refresh_if_needed(
        complex_adv,
        state=cast(Any, state),
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        actual_bid_minor=20_500,
        now=datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC),
    )

    assert result == expected_result
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_main_bid_refresh_if_needed_returns_no_desired_bid() -> None:
    repository = MagicMock()
    repository.save_state = AsyncMock(return_value=None)
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = SimpleNamespace(
        current_mode="main",
        current_main_bid_minor=20_500,
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=None,
        main_started_at=datetime(2026, 6, 15, 11, 0, 0, tzinfo=UTC),
        currency="RUB",
        last_reason=None,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )

    result = await manager.apply_main_bid_refresh_if_needed(
        complex_adv,
        state=cast(Any, state),
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        actual_bid_minor=20_500,
        now=datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC),
    )

    assert result == MainBidRefreshResult.SKIPPED_NO_DESIRED_BID
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_bootstrap_exploration_switches_to_test_before_refresh() -> None:
    analytics = MagicMock()
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=datetime(2026, 6, 14, 0, 0, 0, tzinfo=UTC)
    )
    analytics.get_bid_coverages = AsyncMock(return_value=[])
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
    manager._build_coverage_snapshot = AsyncMock(
        return_value=([], 0, 1, 25_000)
    )  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=60_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        test_started_at=datetime(2026, 6, 15, 11, 0, 0, tzinfo=UTC),
        main_started_at=datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),
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
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=True,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_500,
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=20_500,
            expected_bid_minor=20_500,
            fresh_best_main_bid_minor=20_500,
            fresh_next_test_bid_minor=25_000,
        ),
    )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 25_000
    assert state.main_started_at is None
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_main_mode_historical_manual_force_main_does_not_block_refresh() -> None:
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=60_000)  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = SimpleNamespace(
        current_mode="main",
        current_main_bid_minor=20_500,
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=None,
        main_started_at=datetime(2026, 6, 15, 11, 0, 0, tzinfo=UTC),
        currency="RUB",
        last_reason="manual_force_main",
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )

    result = await manager.apply_main_bid_refresh_if_needed(
        complex_adv,
        state=cast(Any, state),
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        actual_bid_minor=20_500,
        now=datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC),
    )

    assert result == MainBidRefreshResult.APPLIED
    assert state.current_main_bid_minor == 60_000
    manager._choose_main_bid_by_strategy.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_main_mode_retries_refreshed_bid_after_setter_failure() -> None:
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_bid_stats = AsyncMock(return_value=[])
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
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=60_000)  # type: ignore[method-assign]
    manager._maybe_continue_main_exploration = AsyncMock(return_value=(False, None))  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=20_000,
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        test_started_at=datetime(2026, 6, 15, 11, 0, 0, tzinfo=UTC),
        main_started_at=datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),
        current_main_bid_minor=20_500,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        target_main_impressions=10,
        test_share=0.1,
        max_bid_minor=70_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        bot_active=True,
        auto_adv_active_status=True,
        auto_shelf_bid_control_enabled=True,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )

    result = await manager.apply_main_bid_refresh_if_needed(
        complex_adv,
        state=cast(Any, state),
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        actual_bid_minor=20_500,
        now=datetime(2026, 6, 16, 10, 0, 0, tzinfo=UTC),
    )
    assert result == MainBidRefreshResult.APPLIED

    state.current_main_bid_minor = 20_500
    repository.save_state = AsyncMock()
    manager._persist_state_then_set_bid.reset_mock()
    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=20_500,
        snapshot=_synced_progress_snapshot(
            mode="main",
            actual_bid_minor=20_500,
            expected_bid_minor=20_500,
            fresh_best_main_bid_minor=20_500,
        ),
    )
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()


def _fresh_main_snapshot(
    *,
    mode: str = "main",
    actual: int,
    fresh_main: int,
    fresh_test: int | None = 41_000,
) -> AutoShelfBidControlDecisionSnapshot:
    expected = resolve_expected_bid_minor(
        current_mode=mode,
        fresh_best_main_bid_minor=fresh_main,
        fresh_next_test_bid_minor=fresh_test,
        control_enabled=True,
    )
    status = resolve_bid_sync_status(actual, expected)
    return AutoShelfBidControlDecisionSnapshot(
        nmid=1,
        auto_adv_id=2,
        current_mode=mode,
        actual_bid_minor=actual,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=fresh_main,
        fresh_next_test_bid_minor=fresh_test,
        expected_bid_minor=expected,
        bid_sync_status=status,
        can_count_progress=snapshot_can_count_progress(
            expected_bid_minor=expected,
            actual_bid_minor=actual,
            bid_sync_status=status,
        ),
    )


@pytest.mark.asyncio
async def test_fresh_winner_beats_stored_main_state_no_setter_when_actual_matches() -> None:
    manager, repository, wb_bid_setter, state, settings_obj, complex_adv = (
        _build_reconcile_fixture(
            current_mode="main",
            current_test_bid_minor=41_000,
            current_main_bid_minor=48_000,
            actual_bid_minor=57_000,
        )
    )
    snapshot = _fresh_main_snapshot(actual=57_000, fresh_main=57_000)
    manager.build_decision_snapshot = AsyncMock(return_value=snapshot)  # type: ignore[method-assign]
    manager.apply_bid_sync_from_snapshot = AsyncMock(return_value=False)  # type: ignore[method-assign]
    manager._handle_main_mode = AsyncMock()  # type: ignore[method-assign]

    await manager.update(complex_adv)

    assert snapshot.expected_bid_minor == 57_000
    wb_bid_setter.set_bid.assert_not_awaited()
    manager._handle_main_mode.assert_awaited_once()
    assert state.current_main_bid_minor == 48_000


@pytest.mark.asyncio
async def test_fresh_winner_mismatch_calls_setter_once() -> None:
    manager, repository, wb_bid_setter, state, settings_obj, complex_adv = (
        _build_reconcile_fixture(
            current_mode="main",
            current_test_bid_minor=41_000,
            current_main_bid_minor=48_000,
            actual_bid_minor=48_000,
        )
    )
    snapshot = _fresh_main_snapshot(actual=48_000, fresh_main=57_000)
    manager.build_decision_snapshot = AsyncMock(return_value=snapshot)  # type: ignore[method-assign]

    async def _apply_sync(*_args: object, **_kwargs: object) -> bool:
        return await manager._reconcile_expected_bid_for_current_mode(
            complex_adv,
            state=state,
            actual_bid_minor=48_000,
            min_bid_minor=12_000,
            max_bid_minor=80_000,
            now=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
            expected_bid_minor=57_000,
        )

    manager.apply_bid_sync_from_snapshot = AsyncMock(side_effect=_apply_sync)  # type: ignore[method-assign]
    manager._handle_main_mode = AsyncMock()  # type: ignore[method-assign]

    await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once()
    assert wb_bid_setter.set_bid.await_args.kwargs["bid_minor"] == 57_000
    manager._handle_main_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_disabled_control_does_not_enforce_fresh_main() -> None:
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=MagicMock(),
        analytics_repository=MagicMock(),
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=1,
        auto_adv_id=2,
        current_mode="main",
        actual_bid_minor=57_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=41_000,
        expected_bid_minor=None,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
    )
    state = MagicMock()
    state.current_mode = "main"
    result = await manager.apply_bid_sync_from_snapshot(
        MagicMock(),
        state=state,
        snapshot=snapshot,
        control_enabled=False,
        bid_units_confirmed=True,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        now=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )
    assert result is False
    assert snapshot.expected_bid_minor is None


@pytest.mark.asyncio
async def test_apply_bid_sync_skipped_when_actual_bid_unknown() -> None:
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=MagicMock(),
        analytics_repository=MagicMock(),
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=1,
        auto_adv_id=2,
        current_mode="main",
        actual_bid_minor=None,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=41_000,
        expected_bid_minor=57_000,
        bid_sync_status=BidSyncStatus.PENDING,
        can_count_progress=False,
    )
    state = MagicMock()
    state.current_mode = "main"
    manager._reconcile_expected_bid_for_current_mode = AsyncMock(return_value=True)  # type: ignore[method-assign]

    result = await manager.apply_bid_sync_from_snapshot(
        MagicMock(),
        state=state,
        snapshot=snapshot,
        control_enabled=True,
        bid_units_confirmed=True,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        now=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )

    assert result is False
    manager._reconcile_expected_bid_for_current_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_test_mode_does_not_set_waiting_when_bid_not_synced() -> None:
    """Progress-path не ставит TEST_WAITING без synced expected/actual."""
    analytics = MagicMock()
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(bid_minor=20_000, impressions=2_503, valid_hours=1),
        ],
        now_coverages=[
            BidCoverage(bid_minor=20_000, impressions=2_503, valid_hours=1),
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
        max_bid_minor=70_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="test",
        actual_bid_minor=21_000,
        min_bid_minor=12_000,
        max_bid_minor=70_000,
        fresh_best_main_bid_minor=25_000,
        fresh_next_test_bid_minor=20_000,
        expected_bid_minor=20_000,
        bid_sync_status=BidSyncStatus.PENDING,
        can_count_progress=False,
        computed_at=datetime.now(UTC),
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=12_000,
        actual_bid_minor=21_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.BID_SYNC_MISMATCH_NOT_APPLIED
    manager._set_target_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()
    manager._persist_state_then_set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_mode_actual_mismatch_does_not_set_waiting_observation_time() -> None:
    """Mismatch на progress-path блокирует TEST_WAITING и не вызывает setter."""
    analytics = MagicMock()
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
        now_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
    )
    state = MagicMock(
        current_test_bid_minor=50_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=57_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="test",
        actual_bid_minor=7_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=50_000,
        expected_bid_minor=50_000,
        bid_sync_status=BidSyncStatus.MISMATCH_NOT_APPLIED,
        can_count_progress=False,
        computed_at=datetime.now(UTC),
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=7_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.BID_SYNC_MISMATCH_NOT_APPLIED
    assert state.last_reason != ControlReason.TEST_WAITING_OBSERVATION_TIME
    manager._set_target_bid.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_mode_actual_mismatch_does_not_set_waiting_observation_time() -> None:
    """Mismatch на progress-path блокирует MAIN_WAITING и не вызывает setter."""
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
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=41_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(days=2),
        test_started_at=datetime.now(UTC) - timedelta(days=2),
        main_started_at=datetime.now(UTC),
        current_main_bid_minor=57_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=90,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="main",
        actual_bid_minor=48_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=41_000,
        expected_bid_minor=57_000,
        bid_sync_status=BidSyncStatus.MISMATCH_NOT_APPLIED,
        can_count_progress=False,
        computed_at=datetime.now(UTC),
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.BID_SYNC_MISMATCH_NOT_APPLIED
    assert state.last_reason != ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._set_target_bid.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_mode_synced_allows_waiting_observation_time() -> None:
    """Synced test snapshot допускает TEST_WAITING на progress-path."""
    analytics = MagicMock()
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
        now_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
    )
    state = MagicMock(
        current_test_bid_minor=50_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=57_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )
    snapshot = _synced_progress_snapshot(
        mode="test",
        actual_bid_minor=50_000,
        expected_bid_minor=50_000,
        fresh_next_test_bid_minor=50_000,
        fresh_best_main_bid_minor=57_000,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=50_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME
    manager._set_target_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_mode_synced_allows_waiting_observation_time() -> None:
    """Synced main snapshot допускает MAIN_WAITING на progress-path."""
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
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=41_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(days=2),
        test_started_at=datetime.now(UTC) - timedelta(days=2),
        main_started_at=datetime.now(UTC),
        current_main_bid_minor=57_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=90,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = _synced_progress_snapshot(
        mode="main",
        actual_bid_minor=57_000,
        expected_bid_minor=57_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=41_000,
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._set_target_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_disabled_never_sets_observation_waiting_time() -> None:
    """При выключенном control observation waiting не ставится и setter не вызывается."""
    analytics = MagicMock()
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
        now_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
    )
    state = MagicMock(
        current_test_bid_minor=50_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=57_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=False,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )
    snapshot = _synced_progress_snapshot(
        mode="test",
        actual_bid_minor=50_000,
        expected_bid_minor=50_000,
        fresh_next_test_bid_minor=50_000,
        fresh_best_main_bid_minor=57_000,
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=50_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.DISABLED
    assert state.last_reason != ControlReason.TEST_WAITING_OBSERVATION_TIME
    assert state.last_reason != ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._set_target_bid.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_actual_bid_never_sets_observation_waiting_time() -> None:
    """Без фактической ставки observation waiting и setter на progress-path не срабатывают."""
    analytics = MagicMock()
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    _configure_test_coverage(
        analytics,
        first_bucket_start=datetime.now(UTC) - timedelta(hours=4),
        start_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
        now_coverages=[
            BidCoverage(bid_minor=50_000, impressions=2_503, valid_hours=1),
        ],
    )
    state = MagicMock(
        current_test_bid_minor=50_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=57_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="test",
        actual_bid_minor=None,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=50_000,
        expected_bid_minor=50_000,
        bid_sync_status=BidSyncStatus.NO_ACTUAL_BID,
        can_count_progress=False,
        computed_at=datetime.now(UTC),
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=None,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.NO_ACTUAL_BID
    assert state.last_reason != ControlReason.TEST_WAITING_OBSERVATION_TIME
    manager._set_target_bid.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_uses_fresh_snapshot_expected_bid_not_stale_state_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """update/worker path: reconcile берёт expected из fresh snapshot, не из state."""
    manager, repository, wb_bid_setter, state, settings_obj, complex_adv = _build_reconcile_fixture(
        current_mode="main",
        current_test_bid_minor=41_000,
        current_main_bid_minor=48_000,
        actual_bid_minor=48_000,
    )
    settings_obj.max_bid_minor = 80_000
    fresh_snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=30369094,
        auto_adv_id=35018182,
        current_mode="main",
        actual_bid_minor=48_000,
        min_bid_minor=12_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=41_000,
        expected_bid_minor=57_000,
        bid_sync_status=BidSyncStatus.PENDING,
        can_count_progress=False,
        computed_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )
    manager.build_decision_snapshot = AsyncMock(return_value=fresh_snapshot)  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(
        AutoShelfBidControlManager,
        "_now",
        return_value=datetime(2026, 6, 13, 12, 20, 0, tzinfo=UTC),
    ):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=57_000,
        currency="RUB",
    )
    manager._handle_main_mode.assert_not_awaited()
    assert state.current_main_bid_minor == 57_000


@pytest.mark.asyncio
async def test_handle_main_mode_provided_snapshot_ignores_stale_state_main_bid() -> None:
    """Переданный snapshot: main bid из expected/fresh, не из state.current_main_bid_minor."""
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
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=41_000,
        current_mode="main",
        current_cycle_started_at=datetime.now(UTC) - timedelta(days=2),
        test_started_at=datetime.now(UTC) - timedelta(days=2),
        main_started_at=datetime.now(UTC),
        current_main_bid_minor=48_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=90,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="main",
        actual_bid_minor=57_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=41_000,
        expected_bid_minor=57_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        computed_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        snapshot=snapshot,
    )

    assert state.current_main_bid_minor == 57_000
    assert state.current_main_bid_minor != 48_000


@pytest.mark.asyncio
async def test_handle_test_mode_provided_snapshot_ignores_stale_state_test_bid() -> None:
    """Переданный snapshot: test bid из expected, не из state.current_test_bid_minor."""
    analytics = MagicMock()
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._closed_layers_for_bid_at = AsyncMock(side_effect=[0, 0])  # type: ignore[method-assign]
    state = MagicMock(
        current_test_bid_minor=7_000,
        current_mode="test",
        current_cycle_started_at=datetime.now(UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=2),
        main_started_at=None,
        current_main_bid_minor=57_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="test",
        actual_bid_minor=50_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=None,
        expected_bid_minor=50_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        computed_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=50_000,
        snapshot=snapshot,
    )

    assert manager._closed_layers_for_bid_at.await_count == 2
    assert [call.kwargs["bid_minor"] for call in manager._closed_layers_for_bid_at.await_args_list] == [
        50_000,
        50_000,
    ]


@pytest.mark.asyncio
async def test_initialize_does_not_call_set_target_bid_directly() -> None:
    """Initializer только сохраняет state, без прямого setter."""
    repository = MagicMock()
    built_state = MagicMock(last_reason=ControlReason.INITIALIZED)
    repository.build_state = AsyncMock(return_value=built_state)
    repository.save_state = AsyncMock(return_value=built_state)
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    settings_obj = MagicMock(currency="RUB", max_bid_minor=80_000)
    complex_adv = MagicMock(main_nmid=111, auto_adv_id=222)

    await manager._initialize_state(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        min_bid_minor=10_000,
        actual_bid_minor=14_000,
    )

    manager._set_target_bid.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()
    repository.build_state.assert_awaited_once()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_first_update_after_initialize_sets_bid_via_centralized_sync_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")
    """Первый tick инициализирует; второй применяет ставку через sync-path."""
    repository = MagicMock()
    repository.get_settings = AsyncMock()
    repository.repair_settings_units = AsyncMock()
    repository.update_state_reason = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._get_actual_bid = AsyncMock(return_value=14_000)  # type: ignore[method-assign]
    manager._resolve_min_bid_minor = MagicMock(return_value=10_000)  # type: ignore[method-assign]
    manager._is_eligible = MagicMock(  # type: ignore[method-assign]
        return_value=(True, ControlReason.SETTINGS_UPDATED)
    )
    manager._handle_test_mode = AsyncMock()  # type: ignore[method-assign]
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    initialized_state = SimpleNamespace(
        current_mode="test",
        current_test_bid_minor=31_000,
        current_main_bid_minor=14_000,
        current_cycle_started_at=now,
        previous_cycle_started_at=None,
        test_started_at=now,
        main_started_at=None,
        currency="RUB",
        last_reason=ControlReason.INITIALIZED,
    )
    repository.get_state = AsyncMock(side_effect=[None, initialized_state])
    repository.build_state = AsyncMock(return_value=initialized_state)
    repository.save_state = AsyncMock(return_value=initialized_state)
    settings_obj = SimpleNamespace(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
        currency="RUB",
    )
    repository.get_settings.return_value = settings_obj
    repository.repair_settings_units.return_value = settings_obj
    complex_adv = SimpleNamespace(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    fresh_snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=30369094,
        auto_adv_id=35018182,
        current_mode="test",
        actual_bid_minor=14_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=14_000,
        fresh_next_test_bid_minor=31_000,
        expected_bid_minor=31_000,
        bid_sync_status=BidSyncStatus.PENDING,
        can_count_progress=False,
        computed_at=now,
    )
    manager.build_decision_snapshot = AsyncMock(return_value=fresh_snapshot)  # type: ignore[method-assign]
    apply_sync_spy = AsyncMock(wraps=manager.apply_bid_sync_from_snapshot)
    manager.apply_bid_sync_from_snapshot = apply_sync_spy  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager.update(complex_adv)
    wb_bid_setter.set_bid.assert_not_awaited()
    manager._handle_test_mode.assert_not_awaited()
    apply_sync_spy.assert_not_awaited()

    with patch.object(
        AutoShelfBidControlManager,
        "_now",
        return_value=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC),
    ):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=31_000,
        currency="RUB",
    )
    apply_sync_spy.assert_awaited_once()
    assert apply_sync_spy.await_args.kwargs["snapshot"].expected_bid_minor == 31_000
    manager._handle_test_mode.assert_not_awaited()
    assert initialized_state.last_reason == ControlReason.TEST_WAITING_OBSERVATION_TIME


@pytest.mark.asyncio
async def test_mode_transition_does_not_bypass_bid_units_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mode transition сохраняет state без setter при bid_units_confirmed=False."""
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "false")
    manager, repository, state, settings_obj, complex_adv = _configure_plan_distance_test_transition(
        min_bid_minor=8_000,
        max_bid_minor=8_000,
        current_test_bid_minor=8_000,
        covered_anchor_count=0,
        next_test_bid=8_000,
    )
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    wb_bid_setter = manager._setter
    wb_bid_setter.set_bid = AsyncMock()

    await manager._handle_test_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=8_000,
        actual_bid_minor=8_000,
        snapshot=_qualified_main_worker_snapshot(
            mode="test",
            actual_bid_minor=8_000,
            fresh_main_bid_minor=18_000,
            fresh_next_test_bid_minor=8_000,
            min_bid_minor=8_000,
            max_bid_minor=20_000,
        ),
    )

    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_MAIN
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_mode_transition_defers_bid_apply_to_centralized_sync_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")
    """После transition setter вызывается только на следующем тике через apply_bid_sync."""
    manager, repository, state, settings_obj, complex_adv = _configure_plan_distance_test_transition(
        min_bid_minor=8_000,
        max_bid_minor=20_000,
        current_test_bid_minor=8_000,
        covered_anchor_count=0,
        next_test_bid=8_000,
        current_main_bid_minor=18_000,
    )
    repository.get_settings = AsyncMock(return_value=settings_obj)
    repository.repair_settings_units = AsyncMock(return_value=settings_obj)
    repository.get_state = AsyncMock(return_value=state)
    repository.update_state_reason = AsyncMock()
    wb_bid_setter = manager._setter
    wb_bid_setter.set_bid = AsyncMock()
    manager._get_actual_bid = AsyncMock(return_value=8_000)  # type: ignore[method-assign]
    manager._resolve_min_bid_minor = MagicMock(return_value=8_000)  # type: ignore[method-assign]
    manager._is_eligible = MagicMock(  # type: ignore[method-assign]
        return_value=(True, ControlReason.SETTINGS_UPDATED)
    )
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    transition_snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=complex_adv.main_nmid,
        auto_adv_id=complex_adv.auto_adv_id,
        current_mode="test",
        actual_bid_minor=8_000,
        min_bid_minor=8_000,
        max_bid_minor=20_000,
        fresh_best_main_bid_minor=18_000,
        fresh_next_test_bid_minor=8_000,
        expected_bid_minor=8_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        computed_at=now,
    )
    sync_snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=complex_adv.main_nmid,
        auto_adv_id=complex_adv.auto_adv_id,
        current_mode="main",
        actual_bid_minor=8_000,
        min_bid_minor=8_000,
        max_bid_minor=20_000,
        fresh_best_main_bid_minor=18_000,
        fresh_next_test_bid_minor=8_000,
        expected_bid_minor=18_000,
        bid_sync_status=BidSyncStatus.PENDING,
        can_count_progress=False,
        computed_at=now,
    )
    manager.build_decision_snapshot = AsyncMock(  # type: ignore[method-assign]
        side_effect=[transition_snapshot, sync_snapshot],
    )
    real_apply = manager.apply_bid_sync_from_snapshot
    apply_sync_spy = AsyncMock(wraps=real_apply)
    manager.apply_bid_sync_from_snapshot = apply_sync_spy  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )

    with patch.object(AutoShelfBidControlManager, "_now", return_value=now):
        await manager.update(complex_adv)

    assert state.current_mode == "main"
    assert state.last_reason == ControlReason.TEST_COMPLETED_SWITCH_TO_MAIN
    manager._persist_state_then_set_bid.assert_not_awaited()
    repository.save_state.assert_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()

    real_persist = AutoShelfBidControlManager._persist_state_then_set_bid.__get__(
        manager,
        AutoShelfBidControlManager,
    )
    persist_spy = AsyncMock(wraps=real_persist)
    manager._persist_state_then_set_bid = persist_spy  # type: ignore[method-assign]
    apply_sync_spy.reset_mock()

    with patch.object(
        AutoShelfBidControlManager,
        "_now",
        return_value=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC),
    ):
        await manager.update(complex_adv)

    apply_sync_spy.assert_awaited_once()
    persist_spy.assert_awaited_once()
    assert persist_spy.await_args.kwargs["bid_minor"] == 18_000
    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=18_000,
        currency="RUB",
    )


@pytest.mark.asyncio
async def test_worker_mode_transition_uses_snapshot_expected_not_state_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worker/snapshot path: stale state bid не используется как target при transition."""
    analytics = MagicMock()
    analytics.get_impressions = AsyncMock(return_value=999_999)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    )
    analytics.get_bid_coverages = AsyncMock(
        return_value=[BidCoverage(bid_minor=57_000, impressions=4_000, valid_hours=2)]
    )
    repository = MagicMock()
    repository.save_state = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._set_target_bid = AsyncMock()  # type: ignore[method-assign]
    manager._maybe_continue_main_exploration = AsyncMock(  # type: ignore[method-assign]
        return_value=(False, None)
    )
    selector_mock = MagicMock(return_value=57_000)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    state = MagicMock(
        current_test_bid_minor=41_000,
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC),
        test_started_at=datetime.now(UTC) - timedelta(hours=12),
        main_started_at=datetime.now(UTC) - timedelta(hours=10),
        current_main_bid_minor=48_000,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=10,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=111,
        auto_adv_id=222,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=222,
        current_mode="main",
        actual_bid_minor=57_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=57_000,
        expected_bid_minor=57_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        computed_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
    )
    wb_bid_setter = manager._setter
    wb_bid_setter.set_bid = AsyncMock()

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        snapshot=snapshot,
    )

    assert state.last_reason == ControlReason.MAIN_COMPLETED_SWITCH_TO_TEST
    assert state.current_main_bid_minor == 57_000
    assert state.current_main_bid_minor != 48_000
    assert state.current_test_bid_minor == 57_000
    repository.save_state.assert_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    manager._set_target_bid.assert_not_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_enabled_control_without_best_bid_does_not_enforce_stale_main_from_state() -> None:
    """Main mode в state, но <2 qualified bids: handler возвращает в test без setter."""
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    repository = MagicMock()
    repository.save_state = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._maybe_continue_main_exploration = AsyncMock(return_value=(False, None))  # type: ignore[method-assign]
    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=48_000,
        current_test_bid_minor=20_000,
        current_cycle_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        main_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        test_started_at=None,
        currency="RUB",
        last_reason=None,
    )
    settings_obj = MagicMock(
        target_test_impressions=100,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    manager._analytics.get_bid_stats = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            BidStatsDTO(
                bid_minor=20_000,
                currency="RUB",
                mode=None,
                last_interval_at=None,
                impressions=500,
                clicks=20,
                carts=2,
                orders=1,
                spend=100.0,
                cart_cpa=5.0,
                ctr=0.04,
                cart_cr=0.1,
            )
        ]
    )
    manager._build_coverage_snapshot = AsyncMock(return_value=([], 0, 0, 25_000))  # type: ignore[method-assign]

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=20_000,
        control_enabled=True,
    )

    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor is None

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=20_000,
        snapshot=snapshot,
    )

    manager._persist_state_then_set_bid.assert_not_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()
    assert state.current_mode == "test"
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS


@pytest.mark.asyncio
async def test_no_best_bid_sync_applies_next_test_bid_via_centralized_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """<2 qualified bids: setter получает next_test_bid через apply_bid_sync."""
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    repository = MagicMock()
    repository.get_settings = AsyncMock()
    repository.repair_settings_units = AsyncMock()
    repository.update_state_reason = AsyncMock()
    repository.save_state = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._get_actual_bid = AsyncMock(return_value=20_000)  # type: ignore[method-assign]
    manager._resolve_min_bid_minor = MagicMock(return_value=10_000)  # type: ignore[method-assign]
    manager._is_eligible = MagicMock(return_value=(True, ControlReason.SETTINGS_UPDATED))  # type: ignore[method-assign]
    manager._handle_test_mode = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_mode="test",
        current_test_bid_minor=20_000,
        current_main_bid_minor=48_000,
        current_cycle_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=datetime(2026, 6, 13, 11, 0, 0, tzinfo=UTC),
        main_started_at=None,
        currency="RUB",
        last_reason=None,
    )
    repository.get_state = AsyncMock(return_value=state)
    settings_obj = MagicMock(
        target_test_impressions=100,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
        currency="RUB",
    )
    repository.get_settings.return_value = settings_obj
    repository.repair_settings_units.return_value = settings_obj
    complex_adv = SimpleNamespace(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    manager._analytics.get_bid_stats = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            BidStatsDTO(
                bid_minor=20_000,
                currency="RUB",
                mode=None,
                last_interval_at=None,
                impressions=500,
                clicks=20,
                carts=2,
                orders=1,
                spend=100.0,
                cart_cpa=5.0,
                ctr=0.04,
                cart_cr=0.1,
            )
        ]
    )
    manager._build_coverage_snapshot = AsyncMock(return_value=([], 0, 0, 25_000))  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")

    with patch.object(
        AutoShelfBidControlManager,
        "_now",
        return_value=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC),
    ):
        await manager.update(complex_adv)

    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=25_000,
        currency="RUB",
    )
    manager._handle_test_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_main_mode_with_one_qualified_switches_to_test() -> None:
    """mode=main + 1 qualified: revert to test, setter не получает stale 48000."""
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    repository = MagicMock()
    repository.save_state = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=48_000,
        current_test_bid_minor=20_000,
        current_cycle_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        main_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        test_started_at=None,
        currency="RUB",
        last_reason=ControlReason.MAIN_WAITING_OBSERVATION_TIME,
    )
    settings_obj = MagicMock(
        target_test_impressions=100,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    manager._analytics.get_bid_stats = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            BidStatsDTO(
                bid_minor=48_000,
                currency="RUB",
                mode=None,
                last_interval_at=None,
                impressions=500,
                clicks=20,
                carts=2,
                orders=1,
                spend=100.0,
                cart_cpa=5.0,
                ctr=0.04,
                cart_cr=0.1,
            )
        ]
    )
    manager._build_coverage_snapshot = AsyncMock(return_value=([], 0, 0, 50_000))  # type: ignore[method-assign]
    manager._fetch_plan_distance_rec_result = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "view": {
                "plan_ranked": [{"bid": 57_000, "plan_distance_score": 0.1}],
                "best_plan_bid": 48_000,
            },
            "best_plan_bid": 48_000,
        }
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        control_enabled=True,
    )

    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor is None

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        snapshot=snapshot,
    )

    assert state.current_mode == "test"
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    assert state.main_started_at is None
    assert state.current_test_bid_minor == 50_000
    assert state.last_reason != ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_main_mode_insufficient_bids_uses_existing_current_test_bid_when_fresh_next_missing() -> None:
    """main + no best + no fresh_next: fallback на state.current_test_bid_minor."""
    repository = MagicMock()
    repository.save_state = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=48_000,
        current_test_bid_minor=50_000,
        current_cycle_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        main_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        test_started_at=None,
        currency="RUB",
        last_reason=ControlReason.MAIN_WAITING_OBSERVATION_TIME,
    )
    settings_obj = MagicMock(
        target_test_impressions=100,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_enabled=True,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=30369094,
        auto_adv_id=35018182,
        current_mode="main",
        actual_bid_minor=48_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=None,
        fresh_next_test_bid_minor=None,
        expected_bid_minor=None,
        bid_sync_status=BidSyncStatus.MISMATCH_NOT_APPLIED,
        can_count_progress=False,
        qualified_tested_bids_count=1,
        computed_at=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC),
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        snapshot=snapshot,
    )

    assert state.current_mode == "test"
    assert state.current_test_bid_minor == 50_000
    assert state.main_started_at is None
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    assert state.last_reason != ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_mode_insufficient_bids_without_any_test_bid_blocks_cleanly() -> None:
    """main + no best + no test bid: block без setter и без main waiting."""
    repository = MagicMock()
    repository.save_state = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._persist_state_then_set_bid = AsyncMock()  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock()  # type: ignore[method-assign]
    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=48_000,
        current_test_bid_minor=None,
        current_cycle_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        main_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        test_started_at=None,
        currency="RUB",
        last_reason=ControlReason.MAIN_WAITING_OBSERVATION_TIME,
    )
    settings_obj = MagicMock(
        target_test_impressions=100,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_enabled=True,
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=30369094,
        auto_adv_id=35018182,
        current_mode="main",
        actual_bid_minor=48_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=None,
        fresh_next_test_bid_minor=None,
        expected_bid_minor=None,
        bid_sync_status=BidSyncStatus.MISMATCH_NOT_APPLIED,
        can_count_progress=False,
        qualified_tested_bids_count=1,
        computed_at=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC),
    )

    await manager._handle_main_mode(
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        snapshot=snapshot,
    )

    assert state.current_mode == "main"
    assert state.current_main_bid_minor == 48_000
    assert state.last_reason == ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
    assert state.last_reason != ControlReason.MAIN_WAITING_OBSERVATION_TIME
    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._persist_state_then_set_bid.assert_not_awaited()
    wb_bid_setter.set_bid.assert_not_awaited()
    repository.save_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_zero_qualified_bids_starts_test_not_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """0 qualified: test path, expected/enforced = next_test_bid, no main from stale state."""
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    repository = MagicMock()
    repository.get_settings = AsyncMock()
    repository.repair_settings_units = AsyncMock()
    repository.update_state_reason = AsyncMock()
    repository.save_state = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._get_actual_bid = AsyncMock(return_value=48_000)  # type: ignore[method-assign]
    manager._resolve_min_bid_minor = MagicMock(return_value=10_000)  # type: ignore[method-assign]
    manager._is_eligible = MagicMock(return_value=(True, ControlReason.SETTINGS_UPDATED))  # type: ignore[method-assign]
    manager._handle_test_mode = AsyncMock()  # type: ignore[method-assign]
    manager._handle_main_mode = AsyncMock()  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=57_000)  # type: ignore[method-assign]
    state = MagicMock(
        current_mode="test",
        current_test_bid_minor=48_000,
        current_main_bid_minor=48_000,
        current_cycle_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=datetime(2026, 6, 13, 11, 0, 0, tzinfo=UTC),
        main_started_at=None,
        currency="RUB",
        last_reason=None,
    )
    repository.get_state = AsyncMock(return_value=state)
    settings_obj = MagicMock(
        target_test_impressions=100,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
        currency="RUB",
    )
    repository.get_settings.return_value = settings_obj
    repository.repair_settings_units.return_value = settings_obj
    complex_adv = SimpleNamespace(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    manager._analytics.get_bid_stats = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            BidStatsDTO(
                bid_minor=48_000,
                currency="RUB",
                mode=None,
                last_interval_at=None,
                impressions=10,
                clicks=0,
                carts=0,
                orders=0,
                spend=10.0,
                cart_cpa=0.0,
                ctr=0.01,
                cart_cr=0.0,
            )
        ]
    )
    manager._build_coverage_snapshot = AsyncMock(return_value=([], 0, 0, 50_000))  # type: ignore[method-assign]
    manager._fetch_plan_distance_rec_result = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "view": {"plan_ranked": [{"bid": 57_000}], "best_plan_bid": 57_000},
            "best_plan_bid": 57_000,
        }
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")

    with patch.object(
        AutoShelfBidControlManager,
        "_now",
        return_value=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC),
    ):
        await manager.update(complex_adv)

    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._handle_main_mode.assert_not_awaited()
    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=50_000,
        currency="RUB",
    )


@pytest.mark.asyncio
async def test_one_qualified_bid_continues_test_not_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1 qualified: no main, strategy not used, test continues with next_test_bid."""
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    repository = MagicMock()
    repository.get_settings = AsyncMock()
    repository.repair_settings_units = AsyncMock()
    repository.update_state_reason = AsyncMock()
    repository.save_state = AsyncMock()
    wb_bid_setter = MagicMock()
    wb_bid_setter.set_bid = AsyncMock()
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=wb_bid_setter,
        repository=repository,
        analytics_repository=MagicMock(),
    )
    manager._get_actual_bid = AsyncMock(return_value=48_000)  # type: ignore[method-assign]
    manager._resolve_min_bid_minor = MagicMock(return_value=10_000)  # type: ignore[method-assign]
    manager._is_eligible = MagicMock(return_value=(True, ControlReason.SETTINGS_UPDATED))  # type: ignore[method-assign]
    manager._handle_test_mode = AsyncMock()  # type: ignore[method-assign]
    manager._handle_main_mode = AsyncMock()  # type: ignore[method-assign]
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=57_000)  # type: ignore[method-assign]
    state = MagicMock(
        current_mode="test",
        current_test_bid_minor=48_000,
        current_main_bid_minor=48_000,
        current_cycle_started_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        previous_cycle_started_at=None,
        test_started_at=datetime(2026, 6, 13, 11, 0, 0, tzinfo=UTC),
        main_started_at=None,
        currency="RUB",
        last_reason=None,
    )
    repository.get_state = AsyncMock(return_value=state)
    settings_obj = MagicMock(
        target_test_impressions=100,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=80_000,
        min_bid_distance_minor=100,
        currency="RUB",
    )
    repository.get_settings.return_value = settings_obj
    repository.repair_settings_units.return_value = settings_obj
    complex_adv = SimpleNamespace(
        main_nmid=30369094,
        auto_adv_id=35018182,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=None,
        resolve_cpo=None,
    )
    manager._analytics.get_bid_stats = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            BidStatsDTO(
                bid_minor=48_000,
                currency="RUB",
                mode=None,
                last_interval_at=None,
                impressions=500,
                clicks=20,
                carts=2,
                orders=1,
                spend=100.0,
                cart_cpa=5.0,
                ctr=0.04,
                cart_cr=0.1,
            )
        ]
    )
    manager._build_coverage_snapshot = AsyncMock(return_value=([], 0, 0, 50_000))  # type: ignore[method-assign]
    manager._fetch_plan_distance_rec_result = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "view": {"plan_ranked": [{"bid": 57_000}], "best_plan_bid": 57_000},
            "best_plan_bid": 57_000,
        }
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.repair_state_test_bid_minor",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")

    with patch.object(
        AutoShelfBidControlManager,
        "_now",
        return_value=datetime(2026, 6, 13, 12, 5, 0, tzinfo=UTC),
    ):
        await manager.update(complex_adv)

    manager._choose_main_bid_by_strategy.assert_not_awaited()
    manager._handle_main_mode.assert_not_awaited()
    wb_bid_setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=50_000,
        currency="RUB",
    )
