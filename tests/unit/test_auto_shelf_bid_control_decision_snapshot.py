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
    assert snapshot_can_count_progress(BidSyncStatus.SYNCED) is True
    assert snapshot_can_count_progress(BidSyncStatus.PENDING) is False


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
    manager._analytics.get_bid_stats = AsyncMock(return_value=[])  # type: ignore[method-assign]
    manager._fetch_plan_distance_rec_result = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "view": {
                "plan_ranked": [{"bid": 57_000}],
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

    assert snapshot.fresh_best_main_bid_minor == 57_000
    assert snapshot.expected_bid_minor == 57_000
    assert snapshot.best_plan_bid_minor == 48_000
