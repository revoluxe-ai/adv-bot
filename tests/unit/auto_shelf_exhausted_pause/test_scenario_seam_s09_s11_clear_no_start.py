"""Scenario seams S09/S11: clear our-block on tick; no start_auto under other blocker."""

from __future__ import annotations

import pytest

from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_shelf_exhausted_pause.asep_activity_helpers import (
    make_state,
    run_ensure_with_shelf_state,
)
from tests.unit.auto_shelf_exhausted_pause.asep_manager_tick_fixtures import (
    _NOW,
    build_tick_fixture,
    qualified_fit_cycle_stats,
)
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    WB_PAUSE_AUTO_CASES,
    RecordingWbAutoLifecycle,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s09_calendar_due_clears_block_without_forced_start() -> None:
    """S09: calendar due clears PG block; budget blocker ⇒ no start_auto."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            block_active=True,
            due_at=_NOW.replace(year=2020),  # past due
            next_test_bid_minor=None,
            cycle_stats=[],  # no plan-fit → calendar path
            plan_ranked=[{"bid": 15_000, "cpo_rub": 999.0}],  # no fit vs resolve 200
        )
    )

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )
    repository.clear_shelf_exhausted_pause.assert_awaited_once()
    repository.latch_shelf_exhausted_pause.assert_not_awaited()

    # Dual-blocker: our block cleared, but spend exceeds budget → no Auto start.
    wb = RecordingWbAutoLifecycle()
    await run_ensure_with_shelf_state(
        wb=wb,
        state=make_state(pause_active=False, epoch_pending=False),
        auto_status=WBAdvActiveStatus.PAUSE,
        spend_today=500.0,
        auto_budget_daily_limit=100,
    )
    start_case = next(
        c
        for c in WB_PAUSE_AUTO_CASES
        if c.case_id == "start_auto_forbidden_other_blocker"
    )
    wb.assert_matches_case(start_case)
    assert "pause_auto_campaign" not in wb.methods_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s11_plan_fit_clears_block_without_forced_start() -> None:
    """S11: qualified plan-fit on tick clears block; other blocker ⇒ no start."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            block_active=True,
            due_at=_NOW,  # overwritten to future below
            next_test_bid_minor=None,
            cycle_stats=qualified_fit_cycle_stats(),
        )
    )
    # Force future due so calendar path does not win first.
    from datetime import timedelta

    state.shelf_exhausted_due_at = _NOW + timedelta(days=3)

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )
    repository.clear_shelf_exhausted_pause.assert_awaited_once()

    wb = RecordingWbAutoLifecycle()
    await run_ensure_with_shelf_state(
        wb=wb,
        state=make_state(pause_active=False),
        auto_status=WBAdvActiveStatus.PAUSE,
        spend_today=500.0,
        auto_budget_daily_limit=100,
    )
    start_case = next(
        c
        for c in WB_PAUSE_AUTO_CASES
        if c.case_id == "start_auto_forbidden_other_blocker"
    )
    wb.assert_matches_case(start_case)
