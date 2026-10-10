"""Unit tests for decision snapshot pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_decision_snapshot_builder import (
    _resolve_cycle_metric_for_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.optimization_metric import (
    OptimizationMetric,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.decision_snapshot_dto import (
    BidSyncStatus,
    parse_plan_ranked_top_bid_minor,
    resolve_bid_sync_detail,
    resolve_bid_sync_status,
    resolve_expected_bid_minor,
    resolve_primary_status,
    resolve_recommended_main_bid_minor,
    snapshot_can_count_progress,
    can_set_observation_waiting_reason,
    resolve_observation_sync_block_reason,
)

pytestmark = pytest.mark.unit


def test_plan_distance_metric_uses_auto_cpo_not_bad_aggregate_or_search() -> None:
    """Auto Shelf dynamic metric принадлежит Auto leg."""
    complex_adv = MagicMock(
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=999.0,
        auto_fact_cpo=80.0,
        search_fact_cpo=999.0,
        resolve_cpo=100.0,
    )

    metric = _resolve_cycle_metric_for_snapshot(complex_adv)

    assert metric == OptimizationMetric.CTR


def test_plan_distance_metric_missing_auto_cpo_has_no_aggregate_fallback() -> None:
    """Missing Auto CPO не превращается в aggregate-CPO decision."""
    complex_adv = MagicMock(
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        fact_pay_for_order=999.0,
        auto_fact_cpo=None,
        search_fact_cpo=999.0,
        resolve_cpo=100.0,
    )

    metric = _resolve_cycle_metric_for_snapshot(complex_adv)

    assert metric == OptimizationMetric.CPC


def test_resolve_expected_bid_minor_test_mode_uses_next_test() -> None:
    assert (
        resolve_expected_bid_minor(
            current_mode="test",
            fresh_best_main_bid_minor=57_000,
            fresh_next_test_bid_minor=41_000,
            control_enabled=True,
        )
        == 41_000
    )


def test_resolve_expected_bid_minor_main_mode_uses_main_target() -> None:
    assert (
        resolve_expected_bid_minor(
            current_mode="main",
            fresh_best_main_bid_minor=57_000,
            fresh_next_test_bid_minor=41_000,
            control_enabled=True,
        )
        == 57_000
    )


def test_resolve_expected_bid_minor_disabled_returns_none() -> None:
    assert (
        resolve_expected_bid_minor(
            current_mode="main",
            fresh_best_main_bid_minor=57_000,
            fresh_next_test_bid_minor=41_000,
            control_enabled=False,
        )
        is None
    )


def test_bid_sync_status_synced_only_when_actual_matches_expected() -> None:
    assert (
        resolve_bid_sync_status(57_000, 57_000) == BidSyncStatus.SYNCED
    )
    assert (
        resolve_bid_sync_status(48_000, 57_000) == BidSyncStatus.PENDING
    )
    assert (
        resolve_bid_sync_status(48_000, None) == BidSyncStatus.SYNCED
    )
    assert snapshot_can_count_progress(
        expected_bid_minor=57_000,
        actual_bid_minor=57_000,
        bid_sync_status=BidSyncStatus.SYNCED,
    ) is True
    assert snapshot_can_count_progress(
        expected_bid_minor=57_000,
        actual_bid_minor=48_000,
        bid_sync_status=BidSyncStatus.PENDING,
    ) is False
    assert snapshot_can_count_progress(
        expected_bid_minor=None,
        actual_bid_minor=48_000,
        bid_sync_status=BidSyncStatus.SYNCED,
    ) is False


def test_snapshot_expected_none_synced_but_cannot_count_progress() -> None:
    status = resolve_bid_sync_status(48_000, None)
    assert status == BidSyncStatus.SYNCED
    assert (
        snapshot_can_count_progress(
            expected_bid_minor=None,
            actual_bid_minor=48_000,
            bid_sync_status=status,
        )
        is False
    )


def test_snapshot_actual_none_cannot_count_progress() -> None:
    status = resolve_bid_sync_status(None, 50_000)
    assert status == BidSyncStatus.PENDING
    assert (
        snapshot_can_count_progress(
            expected_bid_minor=50_000,
            actual_bid_minor=None,
            bid_sync_status=status,
        )
        is False
    )


def test_snapshot_expected_actual_match_can_count_progress() -> None:
    status = resolve_bid_sync_status(50_000, 50_000)
    assert status == BidSyncStatus.SYNCED
    assert (
        snapshot_can_count_progress(
            expected_bid_minor=50_000,
            actual_bid_minor=50_000,
            bid_sync_status=status,
        )
        is True
    )


def test_resolve_recommended_main_bid_minor_from_plan_ranked_without_min_bid() -> None:
    rec = {
        "plan_ranked": [
            {"bid": 57_000},
            {"bid": 54_000},
            {"bid": 48_000},
        ],
        "best_plan_bid": 48_000,
    }
    assert resolve_recommended_main_bid_minor(rec) == 57_000
    assert (
        resolve_recommended_main_bid_minor(
            rec,
            min_bid_minor=None,
            max_bid_minor=None,
        )
        == 57_000
    )


def test_resolve_recommended_main_bid_minor_clamps_when_range_known() -> None:
    rec = {"plan_ranked": [{"bid": 57_000}]}
    assert (
        resolve_recommended_main_bid_minor(
            rec,
            min_bid_minor=10_000,
            max_bid_minor=50_000,
        )
        == 50_000
    )


def test_resolve_primary_status_disabled_overrides_last_reason() -> None:
    assert (
        resolve_primary_status(
            control_enabled=False,
            last_reason="main_waiting_observation_time",
        )
        == "disabled"
    )


def test_resolve_bid_sync_detail_no_actual_bid_when_enabled_without_actual() -> None:
    assert (
        resolve_bid_sync_detail(
            None,
            57_000,
            control_enabled=True,
        )
        == "no_actual_bid"
    )
    assert (
        resolve_bid_sync_detail(
            None,
            57_000,
            control_enabled=False,
        )
        is None
    )


def test_can_set_observation_waiting_reason_requires_full_sync() -> None:
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.decision_snapshot_dto import (
        AutoShelfBidControlDecisionSnapshot,
    )

    synced = AutoShelfBidControlDecisionSnapshot(
        nmid=1,
        auto_adv_id=2,
        current_mode="test",
        actual_bid_minor=20_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=25_000,
        fresh_next_test_bid_minor=20_000,
        expected_bid_minor=20_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
    )
    assert (
        can_set_observation_waiting_reason(
            control_enabled=True,
            snapshot=synced,
        )
        is True
    )
    assert (
        can_set_observation_waiting_reason(
            control_enabled=False,
            snapshot=synced,
        )
        is False
    )
    mismatch_snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=1,
        auto_adv_id=2,
        current_mode="test",
        actual_bid_minor=21_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=25_000,
        fresh_next_test_bid_minor=20_000,
        expected_bid_minor=20_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
    )
    assert (
        can_set_observation_waiting_reason(
            control_enabled=True,
            snapshot=mismatch_snapshot,
        )
        is False
    )
    pending = AutoShelfBidControlDecisionSnapshot(
        nmid=1,
        auto_adv_id=2,
        current_mode="test",
        actual_bid_minor=21_000,
        min_bid_minor=10_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=25_000,
        fresh_next_test_bid_minor=20_000,
        expected_bid_minor=20_000,
        bid_sync_status=BidSyncStatus.PENDING,
        can_count_progress=False,
    )
    assert (
        can_set_observation_waiting_reason(
            control_enabled=True,
            snapshot=pending,
        )
        is False
    )
    assert (
        resolve_observation_sync_block_reason(
            control_enabled=False,
            snapshot=synced,
        )
        == "disabled"
    )
    assert (
        resolve_observation_sync_block_reason(
            control_enabled=True,
            snapshot=pending,
        )
        == "bid_sync_mismatch_not_applied"
    )


def test_parse_plan_ranked_top_bid_minor_reads_first_ranked_row() -> None:
    assert parse_plan_ranked_top_bid_minor(
        {
            "plan_ranked": [{"bid": 57_000}, {"bid": 48_000}],
            "best_plan_bid": 48_000,
        }
    ) == 57_000


@pytest.mark.asyncio
async def test_decision_snapshot_uses_plan_ranked_top_not_best_plan_bid() -> None:
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=MagicMock(),
        analytics_repository=MagicMock(),
    )
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    state.previous_cycle_started_at = None

    manager._build_coverage_snapshot = AsyncMock(  # type: ignore[method-assign]
        return_value=([], 0, 0, 41_000)
    )
    manager._analytics.get_bid_stats = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            BidStatsDTO(
                bid_minor=57_000,
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
                bid_minor=48_000,
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
    manager._fetch_plan_distance_rec_result = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "view": {
                "plan_ranked": [
                    {"bid": 57_000},
                    {"bid": 48_000},
                ],
                "best_plan_bid": 48_000,
            },
            "best_plan_bid": 48_000,
        }
    )
    settings_obj = MagicMock()
    settings_obj.max_bid_minor = 80_000
    settings_obj.target_test_impressions = 100
    settings_obj.target_test_observation_minutes = 60
    settings_obj.min_bid_distance_minor = 100
    complex_adv = MagicMock()
    complex_adv.main_nmid = 1
    complex_adv.auto_adv_id = 2
    complex_adv.fact_pay_for_order = None
    complex_adv.resolve_cpo = None
    complex_adv.auto_shelf_bid_control_strategy = (
        AutoShelfBidControlStrategy.PLAN_DISTANCE
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 2
    assert snapshot.fresh_best_main_bid_minor == 57_000
    assert snapshot.expected_bid_minor == 57_000
    assert snapshot.best_plan_bid_minor == 48_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"] == [
        {"bid": 57_000},
        {"bid": 48_000},
    ]


def _cycle_bid_stat(
    bid_minor: int,
    *,
    impressions: int = 500,
    clicks: int = 20,
    cart_cpa: float = 5.0,
    ctr: float = 0.04,
) -> "BidStatsDTO":
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    return BidStatsDTO(
        bid_minor=bid_minor,
        currency="RUB",
        mode=None,
        last_interval_at=None,
        impressions=impressions,
        clicks=clicks,
        carts=2,
        orders=1,
        spend=100.0,
        cart_cpa=cart_cpa,
        ctr=ctr,
        cart_cr=0.1,
    )


def _cycle_metric_manager(
    cycle_stats: list["BidStatsDTO"],
) -> AutoShelfBidControlManager:
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=MagicMock(),
        analytics_repository=MagicMock(),
    )
    manager._build_coverage_snapshot = AsyncMock(return_value=([], 0, 0, 41_000))  # type: ignore[method-assign]
    manager._analytics.get_bid_stats = AsyncMock(return_value=cycle_stats)  # type: ignore[method-assign]
    manager._analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return manager


@pytest.mark.asyncio
async def test_decision_snapshot_one_qualified_tested_bid_has_no_main_recommendation() -> None:
    manager = _cycle_metric_manager([_cycle_bid_stat(20_000)])
    state = MagicMock()
    state.current_mode = "test"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=20_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 1
    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor == snapshot.fresh_next_test_bid_minor
    assert snapshot.main_target_explanation == "недостаточно протестированных ставок"


@pytest.mark.asyncio
async def test_decision_snapshot_two_qualified_tested_bids_selects_ranked_best() -> None:
    manager = _cycle_metric_manager(
        [
            _cycle_bid_stat(57_000, cart_cpa=4.0, ctr=0.05),
            _cycle_bid_stat(48_000, cart_cpa=6.0, ctr=0.03),
        ]
    )
    manager._analytics.get_best_bid_by_cart_cpa = AsyncMock(  # type: ignore[method-assign]
        return_value=_cycle_bid_stat(57_000, cart_cpa=4.0, ctr=0.05)
    )
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 2
    assert snapshot.fresh_best_main_bid_minor == 57_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 57_000
    assert snapshot.expected_bid_minor == 57_000


@pytest.mark.asyncio
async def test_decision_snapshot_legacy_cycle_metric_fallback_uses_cpc_ranking() -> None:
    manager = _cycle_metric_manager(
        [
            _cycle_bid_stat(57_000, cart_cpa=7.0, ctr=0.06),
            _cycle_bid_stat(48_000, cart_cpa=4.0, ctr=0.03),
        ]
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    state.previous_cycle_started_at = None
    state.current_main_bid_minor = 57_000
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=1.0,
        resolve_cpo=10.0,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CYCLE_METRIC,
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        control_enabled=True,
    )

    assert snapshot.fresh_best_main_bid_minor == 48_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 48_000


@pytest.mark.asyncio
async def test_decision_snapshot_ctr_strategy_uses_strategy_resolver_for_main_bid() -> None:
    manager = _cycle_metric_manager(
        [
            _cycle_bid_stat(57_000, cart_cpa=4.0, ctr=0.05),
            _cycle_bid_stat(48_000, cart_cpa=6.0, ctr=0.03),
        ]
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=48_000)  # type: ignore[method-assign]
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    state.previous_cycle_started_at = None
    state.current_main_bid_minor = 57_000
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CTR,
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        control_enabled=True,
    )

    manager._choose_main_bid_by_strategy.assert_awaited_once()
    assert snapshot.fresh_best_main_bid_minor == 48_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 57_000


@pytest.mark.asyncio
async def test_decision_snapshot_cpc_strategy_uses_strategy_resolver_for_main_bid() -> None:
    manager = _cycle_metric_manager(
        [
            _cycle_bid_stat(57_000, impressions=500, clicks=20, cart_cpa=4.0, ctr=0.05),
            _cycle_bid_stat(48_000, impressions=500, clicks=15, cart_cpa=6.0, ctr=0.03),
        ]
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=57_000)  # type: ignore[method-assign]
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    state.previous_cycle_started_at = None
    state.current_main_bid_minor = 48_000
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CPC,
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        control_enabled=True,
    )

    manager._choose_main_bid_by_strategy.assert_awaited_once()
    assert snapshot.fresh_best_main_bid_minor == 57_000


@pytest.mark.asyncio
async def test_decision_snapshot_cpc_fallback_keeps_cpc_ranking() -> None:
    manager = _cycle_metric_manager(
        [
            _cycle_bid_stat(57_000, impressions=500, clicks=20, cart_cpa=7.0, ctr=0.06),
            _cycle_bid_stat(48_000, impressions=500, clicks=15, cart_cpa=4.0, ctr=0.03),
        ]
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    state.previous_cycle_started_at = None
    state.current_main_bid_minor = 57_000
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=1.0,
        resolve_cpo=10.0,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CPC,
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        control_enabled=True,
    )

    assert snapshot.fresh_best_main_bid_minor == 48_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 48_000


@pytest.mark.asyncio
async def test_decision_snapshot_ctr_fallback_keeps_ctr_ranking() -> None:
    manager = _cycle_metric_manager(
        [
            _cycle_bid_stat(57_000, impressions=500, clicks=20, cart_cpa=4.0, ctr=0.03),
            _cycle_bid_stat(48_000, impressions=500, clicks=15, cart_cpa=7.0, ctr=0.06),
        ]
    )
    manager._choose_main_bid_by_strategy = AsyncMock(return_value=None)  # type: ignore[method-assign]
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    state.previous_cycle_started_at = None
    state.current_main_bid_minor = 57_000
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=10.0,
        resolve_cpo=1.0,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CTR,
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=57_000,
        control_enabled=True,
    )

    assert snapshot.fresh_best_main_bid_minor == 48_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 48_000


def _plan_distance_rec_view() -> dict[str, object]:
    return {
        "plan_ranked": [
            {"bid": 57_000, "plan_distance_score": 0.1},
            {"bid": 54_000, "plan_distance_score": 0.2},
            {"bid": 48_000, "plan_distance_score": 0.3},
        ],
        "best_plan_bid": 48_000,
    }


def _plan_distance_manager(
    *,
    cycle_stats: list[object],
    rec_view: dict[str, object] | None = None,
    coverage_next_test: int | None = 50_000,
) -> AutoShelfBidControlManager:
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=MagicMock(),
        analytics_repository=MagicMock(),
    )
    manager._build_coverage_snapshot = AsyncMock(  # type: ignore[method-assign]
        return_value=([], 0, 0, coverage_next_test)
    )
    manager._analytics.get_bid_stats = AsyncMock(return_value=cycle_stats)  # type: ignore[method-assign]
    manager._fetch_plan_distance_rec_result = AsyncMock(  # type: ignore[method-assign]
        return_value={"view": rec_view or _plan_distance_rec_view(), "best_plan_bid": 48_000}
    )
    return manager


@pytest.mark.asyncio
async def test_zero_qualified_bids_starts_test_not_main() -> None:
    manager = _plan_distance_manager(
        cycle_stats=[_cycle_bid_stat(48_000, impressions=10, clicks=0)],
        coverage_next_test=50_000,
    )
    state = MagicMock()
    state.current_mode = "test"
    state.current_main_bid_minor = 48_000
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            plan_for_sales_for_day=10.0,
            target_price_for_order=100.0,
            max_price_for_order=200.0,
        ),
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 0
    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor == 50_000
    assert snapshot.fresh_next_test_bid_minor == 50_000


@pytest.mark.asyncio
async def test_decision_snapshot_zero_qualified_bids_no_main_and_expected_test_bid() -> None:
    manager = _plan_distance_manager(
        cycle_stats=[_cycle_bid_stat(20_000, impressions=10, clicks=0)],
        coverage_next_test=41_000,
    )
    state = MagicMock()
    state.current_mode = "test"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            plan_for_sales_for_day=10.0,
            target_price_for_order=100.0,
            max_price_for_order=200.0,
        ),
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=20_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 0
    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor == 41_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 57_000


@pytest.mark.asyncio
async def test_one_qualified_bid_continues_test_not_main() -> None:
    manager = _plan_distance_manager(
        cycle_stats=[_cycle_bid_stat(48_000, impressions=500, clicks=20)],
        coverage_next_test=50_000,
    )
    state = MagicMock()
    state.current_mode = "test"
    state.current_main_bid_minor = 48_000
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            plan_for_sales_for_day=10.0,
            target_price_for_order=100.0,
            max_price_for_order=200.0,
        ),
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 1
    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor == 50_000
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 57_000


@pytest.mark.asyncio
async def test_insufficient_qualified_bids_does_not_use_stale_state_main() -> None:
    manager = _plan_distance_manager(
        cycle_stats=[_cycle_bid_stat(48_000, impressions=500, clicks=20)],
        coverage_next_test=50_000,
    )
    state = MagicMock()
    state.current_mode = "main"
    state.current_main_bid_minor = 48_000
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            plan_for_sales_for_day=10.0,
            target_price_for_order=100.0,
            max_price_for_order=200.0,
        ),
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 1
    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor is None
    assert snapshot.rec_bid_recommendation is not None
    assert snapshot.rec_bid_recommendation["plan_ranked"][0]["bid"] == 57_000


@pytest.mark.asyncio
async def test_insufficient_qualified_bids_prefers_next_test_bid() -> None:
    manager = _plan_distance_manager(
        cycle_stats=[_cycle_bid_stat(20_000, impressions=500, clicks=20)],
        coverage_next_test=50_000,
    )
    state = MagicMock()
    state.current_mode = "test"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            plan_for_sales_for_day=10.0,
            target_price_for_order=100.0,
            max_price_for_order=200.0,
        ),
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=20_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 1
    assert snapshot.fresh_best_main_bid_minor is None
    assert snapshot.expected_bid_minor == 50_000
    assert snapshot.fresh_next_test_bid_minor == 50_000


@pytest.mark.asyncio
async def test_two_qualified_bids_allows_main_best() -> None:
    manager = _plan_distance_manager(
        cycle_stats=[
            _cycle_bid_stat(57_000, impressions=500, clicks=20, cart_cpa=4.0, ctr=0.05),
            _cycle_bid_stat(48_000, impressions=500, clicks=15, cart_cpa=6.0, ctr=0.03),
        ],
    )
    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = MagicMock()
    settings_obj = MagicMock(
        max_bid_minor=80_000,
        target_test_impressions=100,
        target_test_observation_minutes=60,
        min_bid_distance_minor=100,
    )
    complex_adv = MagicMock(
        main_nmid=1,
        auto_adv_id=2,
        fact_pay_for_order=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        adv_setting=MagicMock(
            plan_for_sales_for_day=10.0,
            target_price_for_order=100.0,
            max_price_for_order=200.0,
        ),
    )

    snapshot = await manager.build_decision_snapshot(
        complex_adv,
        settings_obj=settings_obj,
        state=state,
        min_bid_minor=10_000,
        actual_bid_minor=48_000,
        control_enabled=True,
    )

    assert snapshot.qualified_tested_bids_count == 2
    assert snapshot.fresh_best_main_bid_minor == 57_000
    assert snapshot.expected_bid_minor == 57_000


def test_resolve_expected_bid_minor_main_without_fresh_best_is_none() -> None:
    assert (
        resolve_expected_bid_minor(
            current_mode="main",
            fresh_best_main_bid_minor=None,
            fresh_next_test_bid_minor=50_000,
            control_enabled=True,
        )
        is None
    )
