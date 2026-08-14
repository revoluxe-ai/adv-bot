"""Shared fixtures for ASEP manager-tick scenario_seam tests (S01/S02/S06/S09/S11).

Production entry: ``AutoShelfBidControlManager._apply_shelf_exhausted_tick``.
WB thin end stays silent on these hops (PG latch/clear only in tick).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
    BidStatsDTO,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.decision_snapshot_dto import (
    AutoShelfBidControlDecisionSnapshot,
    BidSyncStatus,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.optimization_metric import (
    OptimizationMetric,
)

_NOW = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)
_RESOLVE_CPO = 200.0
_FIT_CPO = 180.0
_FIT_BID = 15_000
_TARGET_IMPRESSIONS = 100


def qualified_fit_cycle_stats() -> list[BidStatsDTO]:
    """Cycle stats where plan-fit bid is qualified-tested."""
    return [
        BidStatsDTO(
            bid_minor=_FIT_BID,
            currency="RUB",
            mode=None,
            last_interval_at=None,
            impressions=_TARGET_IMPRESSIONS + 10,
            clicks=5,
            carts=1,
            orders=0,
            spend=50.0,
            cart_cpa=50.0,
            ctr=0.05,
            cart_cr=0.2,
        )
    ]


def empty_cycle_stats() -> list[BidStatsDTO]:
    """No impressions → empty qualified set."""
    return []


def build_tick_fixture(
    *,
    module_enabled: bool = True,
    strategy: AutoShelfBidControlStrategy = AutoShelfBidControlStrategy.PLAN_DISTANCE,
    block_active: bool = False,
    due_at: datetime | None = None,
    next_test_bid_minor: int | None = None,
    cycle_stats: list[BidStatsDTO] | None = None,
    plan_ranked: list[dict[str, object]] | None = None,
) -> tuple[
    AutoShelfBidControlManager,
    MagicMock,
    Any,
    Any,
    Any,
    AutoShelfBidControlDecisionSnapshot,
]:
    """Manager + repo stubs for production ``_apply_shelf_exhausted_tick``."""
    repository = MagicMock()
    repository.get_state = AsyncMock()
    repository.latch_shelf_exhausted_pause = AsyncMock()
    repository.clear_shelf_exhausted_pause = AsyncMock()

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(
        return_value=cycle_stats if cycle_stats is not None else empty_cycle_stats()
    )

    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._now = staticmethod(lambda: _NOW)  # type: ignore[method-assign]

    if due_at is None and block_active:
        due_at = _NOW + timedelta(days=7)

    state = SimpleNamespace(
        nmid=30_369_094,
        current_mode="main",
        current_test_bid_minor=None,
        current_main_bid_minor=12_000,
        current_cycle_started_at=_NOW - timedelta(days=1),
        previous_cycle_started_at=_NOW - timedelta(days=2),
        currency="RUB",
        shelf_exhausted_pause_active=block_active,
        shelf_exhausted_due_at=due_at,
        shelf_exhausted_resolve_cpo_kind="target",
        shelf_exhausted_resolve_cpo_value=_RESOLVE_CPO,
    )
    repository.get_state.return_value = state

    settings_obj = SimpleNamespace(
        target_test_impressions=_TARGET_IMPRESSIONS,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=50_000,
        retest_interval_days=7,
    )
    complex_adv = SimpleNamespace(
        main_nmid=30_369_094,
        auto_adv_id=35_018_182,
        auto_shelf_bid_control_enabled=module_enabled,
        auto_shelf_bid_control_strategy=strategy,
        plan=None,
        fact_predict_orders=None,
        resolve_cpo=_RESOLVE_CPO,
        resolve_cpo_kind="target",
        fact_pay_for_order=None,
    )
    if plan_ranked is None:
        plan_ranked = [{"bid": _FIT_BID, "cpo_rub": _FIT_CPO}]
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=30_369_094,
        auto_adv_id=35_018_182,
        current_mode="main",
        actual_bid_minor=12_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        fresh_best_main_bid_minor=12_000,
        fresh_next_test_bid_minor=next_test_bid_minor,
        expected_bid_minor=12_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        rec_bid_recommendation={"plan_ranked": plan_ranked},
        qualified_tested_bids_count=0,
        computed_at=_NOW,
    )
    return manager, repository, state, settings_obj, complex_adv, snapshot


__all__ = [
    "OptimizationMetric",
    "_FIT_BID",
    "_FIT_CPO",
    "_NOW",
    "_RESOLVE_CPO",
    "build_tick_fixture",
    "empty_cycle_stats",
    "qualified_fit_cycle_stats",
]
