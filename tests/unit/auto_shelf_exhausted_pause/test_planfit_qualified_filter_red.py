"""RED regression: terminal plan-fit MUST honor qualified_tested on manager tick.

Bug ROOT-001 / BUGCASE-ASEP-PLANFIT: ``_apply_shelf_exhausted_tick`` hard-codes
``qualified_tested_bid_minors=None``, so untested plan_ranked rows with CPO≤resolve
count as plan_fit (skip latch / false-clear our-block).

Invariant: only qualified-tested bids may drive plan-fit on the production tick.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

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
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.qualified_tested_bids import (
    collect_qualified_tested_bid_minors,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.optimization_metric import (
    OptimizationMetric,
)

# Untested plan-ranked bid that would "fit" if qualified filter is ignored.
_UNTESTED_FIT_BID_MINOR = 15_000
_RESOLVE_CPO = 200.0
_FIT_CPO = 180.0
_TARGET_TEST_IMPRESSIONS = 100
_NOW = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)


def _untested_cycle_stats() -> list[BidStatsDTO]:
    """Cycle stats where the only plan-fit bid lacks qualified impressions."""
    return [
        BidStatsDTO(
            bid_minor=_UNTESTED_FIT_BID_MINOR,
            currency="RUB",
            mode=None,
            last_interval_at=None,
            impressions=5,  # << target_test_impressions → not qualified
            clicks=1,
            carts=0,
            orders=0,
            spend=10.0,
            cart_cpa=10.0,
            ctr=0.2,
            cart_cr=0.0,
        )
    ]


def _assert_fixture_excludes_fit_bid_from_qualified() -> None:
    """Sanity: after GO wiring, collect() must exclude the untested fit bid."""
    qualified = collect_qualified_tested_bid_minors(
        _untested_cycle_stats(),
        target_test_impressions=_TARGET_TEST_IMPRESSIONS,
        metric=OptimizationMetric.CTR,
    )
    assert _UNTESTED_FIT_BID_MINOR not in qualified
    assert qualified == []


def _build_manager_fixture(
    *,
    block_active: bool,
) -> tuple[
    AutoShelfBidControlManager,
    MagicMock,
    Any,
    Any,
    Any,
    AutoShelfBidControlDecisionSnapshot,
]:
    """Manager + PG repo stubs for production ``_apply_shelf_exhausted_tick``."""
    _assert_fixture_excludes_fit_bid_from_qualified()

    repository = MagicMock()
    repository.get_state = AsyncMock()
    repository.latch_shelf_exhausted_pause = AsyncMock()
    repository.clear_shelf_exhausted_pause = AsyncMock()

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_untested_cycle_stats())

    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    manager._now = staticmethod(lambda: _NOW)  # type: ignore[method-assign]

    state = SimpleNamespace(
        nmid=30_369_094,
        current_mode="main",
        current_test_bid_minor=None,
        current_main_bid_minor=12_000,
        current_cycle_started_at=_NOW - timedelta(days=1),
        previous_cycle_started_at=_NOW - timedelta(days=2),
        currency="RUB",
        shelf_exhausted_pause_active=block_active,
        shelf_exhausted_due_at=_NOW + timedelta(days=7) if block_active else None,
        shelf_exhausted_resolve_cpo_kind="target",
        shelf_exhausted_resolve_cpo_value=_RESOLVE_CPO,
    )
    repository.get_state.return_value = state

    settings_obj = SimpleNamespace(
        target_test_impressions=_TARGET_TEST_IMPRESSIONS,
        target_test_observation_minutes=60,
        test_share=0.1,
        max_bid_minor=50_000,
        retest_interval_days=7,
    )
    complex_adv = SimpleNamespace(
        main_nmid=30_369_094,
        auto_adv_id=35_018_182,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        plan=None,
        fact_predict_orders=None,
        resolve_cpo=_RESOLVE_CPO,
        resolve_cpo_kind="target",
    )
    snapshot = AutoShelfBidControlDecisionSnapshot(
        nmid=30_369_094,
        auto_adv_id=35_018_182,
        current_mode="main",
        actual_bid_minor=12_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        fresh_best_main_bid_minor=12_000,
        fresh_next_test_bid_minor=None,  # epoch exhausted
        expected_bid_minor=12_000,
        bid_sync_status=BidSyncStatus.SYNCED,
        can_count_progress=True,
        rec_bid_recommendation={
            "plan_ranked": [
                {"bid": _UNTESTED_FIT_BID_MINOR, "cpo_rub": _FIT_CPO},
            ]
        },
        qualified_tested_bids_count=0,
        computed_at=_NOW,
    )
    return manager, repository, state, settings_obj, complex_adv, snapshot


@pytest.mark.asyncio
async def test_manager_tick_latches_when_only_plan_fit_bid_is_untested() -> None:
    """Production tick: untested plan_ranked fit MUST NOT skip latch.

    RED before GO: hard-coded ``None`` treats untested fit as plan_fit → no latch.
    After wiring collect_qualified_tested_bid_minors → empty qualified → latch.
    """
    manager, repository, _state, settings_obj, complex_adv, snapshot = (
        _build_manager_fixture(block_active=False)
    )

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=_state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    repository.latch_shelf_exhausted_pause.assert_awaited_once()
    repository.clear_shelf_exhausted_pause.assert_not_awaited()
    latch_kwargs = repository.latch_shelf_exhausted_pause.await_args.kwargs
    assert latch_kwargs["resolve_cpo_kind"] == "target"
    assert float(latch_kwargs["resolve_cpo_value"]) == _RESOLVE_CPO


@pytest.mark.asyncio
async def test_manager_tick_keeps_block_when_only_plan_fit_bid_is_untested() -> None:
    """Active our-block: untested plan_ranked fit MUST NOT false-clear.

    RED before GO: ``None`` → false plan_fit → clear_fit.
    After wiring → kept_block (clear not called).
    """
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        _build_manager_fixture(block_active=True)
    )

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    repository.clear_shelf_exhausted_pause.assert_not_awaited()
    repository.latch_shelf_exhausted_pause.assert_not_awaited()
