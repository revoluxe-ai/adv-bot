"""Regression: epoch_pending must not stick when Auto is already STARTED.

Bug ROOT-001 / BUGCASE-ASEP-EPOCH-PENDING-STUCK
(HUNT PBH-EPOCH-PENDING-STUCK-001):

After calendar / plan-fit clear sets ``shelf_exhausted_epoch_pending=True``,
``mark_shelf_exhausted_epoch_started`` historically ran only on the Auto
*start* transition (``_maybe_open_shelf_exhausted_epoch``). If Auto was
already ``STARTED``, that mark never ran. While ``epoch_pending`` stayed
True, ``should_latch_terminal_block`` returned
``noop_epoch_pending_awaiting_new_epoch`` forever — a later exhausted
epoch with no plan-fit could never latch again.

Failing-before-fix: STARTED branch skipped
``_maybe_open_shelf_exhausted_epoch`` → mark not awaited → fixture pending
stuck → later tick ``noop_epoch_pending_awaiting_new_epoch``.

Fix: activity also opens/consumes pending when Auto is already STARTED
(same helper as start-transition). Distinct from GH001 (do not re-latch
*before* a new Auto epoch when start is still expected / pending held).
"""

from __future__ import annotations

# pyright: reportPrivateUsage=false

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.apply_tick import (
    apply_shelf_exhausted_tick,
)
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
    RecordingWbAutoLifecycle,
)


def _apply_clear_side_effect(state: Any) -> Any:
    """Mirror production ``clear_shelf_exhausted_pause_in_session`` on fixture state."""

    async def _clear(_nmid: int) -> bool:
        if not bool(state.shelf_exhausted_pause_active):
            return False
        state.shelf_exhausted_pause_active = False
        state.shelf_exhausted_paused_at = None
        state.shelf_exhausted_due_at = None
        state.shelf_exhausted_epoch_pending = True
        state.shelf_exhausted_notify_sent_at = None
        return True

    return _clear


async def _assert_later_exhausted_tick_not_stuck(
    *,
    repository: Any,
    complex_adv: Any,
    settings_obj: Any,
    state: Any,
    snapshot: Any,
) -> None:
    """Later exhausted + no plan-fit must latch or consume pending (not stuck noop)."""
    # Remove plan-fit so detect would otherwise latch (empty next_test_bid).
    snapshot.rec_bid_recommendation = {
        "plan_ranked": [{"bid": 15_000, "cpo_rub": 999.0}]
    }
    repository.latch_shelf_exhausted_pause.reset_mock()

    outcome = await apply_shelf_exhausted_tick(
        repository=repository,
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        snapshot=snapshot,
        now=_NOW,
        qualified_tested_bid_minors=[],
    )

    pending_stuck = bool(state.shelf_exhausted_epoch_pending)
    latched = repository.latch_shelf_exhausted_pause.await_count >= 1
    pending_consumed = not pending_stuck
    assert latched or pending_consumed, (
        "epoch_pending stuck forever after Auto-already-STARTED "
        f"(no mark_shelf_exhausted_epoch_started): outcome={outcome!r} "
        f"pending={state.shelf_exhausted_epoch_pending!r}; "
        "expected latch or pending consume on exhausted+no plan-fit tick"
    )


async def _activity_consume_pending_when_already_started(
    *,
    fixture_state: Any,
) -> None:
    """Activity hop with Auto already STARTED must open/consume epoch_pending.

    Production mark writes the same PG row the shelf tick reads; the activity
    helper uses a separate ``make_state`` mock, so after mark we mirror the
    DB clear onto the tick fixture SoT.
    """
    wb = RecordingWbAutoLifecycle()
    activity_state = make_state(pause_active=False, epoch_pending=True)
    reason = await run_ensure_with_shelf_state(
        wb=wb,
        state=activity_state,
        auto_status=WBAdvActiveStatus.STARTED,
        spend_today=10.0,
        auto_budget_daily_limit=1000,
    )
    assert "start_auto_campaign" not in wb.methods_called()
    repo = reason.shelf_repo  # type: ignore[attr-defined]
    repo.mark_shelf_exhausted_epoch_started.assert_awaited_once()
    # Mirror production mark_shelf_exhausted_epoch_started on tick SoT.
    fixture_state.shelf_exhausted_epoch_pending = False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plan_fit_clear_auto_already_started_later_exhausted_must_latch_or_consume_pending() -> None:
    """Plan-fit clear → pending; Auto STARTED consumes mark; later tick not stuck."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            block_active=True,
            due_at=_NOW + timedelta(days=3),
            next_test_bid_minor=None,
            cycle_stats=qualified_fit_cycle_stats(),
        )
    )
    state.shelf_exhausted_epoch_pending = False
    repository.clear_shelf_exhausted_pause = AsyncMock(
        side_effect=_apply_clear_side_effect(state)
    )
    repository.get_state = AsyncMock(return_value=state)

    # Tick 1: plan-fit clear our-block + set epoch_pending.
    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )
    repository.clear_shelf_exhausted_pause.assert_awaited_once()
    assert state.shelf_exhausted_pause_active is False
    assert state.shelf_exhausted_epoch_pending is True

    await _activity_consume_pending_when_already_started(fixture_state=state)
    assert state.shelf_exhausted_epoch_pending is False

    # Empty qualified set on later tick (no new testing coverage yet).
    analytics = manager._analytics
    analytics.get_bid_stats = AsyncMock(return_value=[])

    await _assert_later_exhausted_tick_not_stuck(
        repository=repository,
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        snapshot=snapshot,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calendar_clear_auto_already_started_later_exhausted_must_latch_or_consume_pending() -> None:
    """Calendar clear → pending; Auto STARTED consumes mark; later tick not stuck."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            block_active=True,
            due_at=_NOW.replace(year=2020),
            next_test_bid_minor=None,
            cycle_stats=[],
            plan_ranked=[{"bid": 15_000, "cpo_rub": 999.0}],
        )
    )
    state.shelf_exhausted_epoch_pending = False
    repository.clear_shelf_exhausted_pause = AsyncMock(
        side_effect=_apply_clear_side_effect(state)
    )
    repository.get_state = AsyncMock(return_value=state)

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )
    repository.clear_shelf_exhausted_pause.assert_awaited_once()
    assert state.shelf_exhausted_epoch_pending is True

    await _activity_consume_pending_when_already_started(fixture_state=state)
    assert state.shelf_exhausted_epoch_pending is False

    analytics = manager._analytics
    analytics.get_bid_stats = AsyncMock(return_value=[])

    await _assert_later_exhausted_tick_not_stuck(
        repository=repository,
        complex_adv=complex_adv,
        settings_obj=settings_obj,
        state=state,
        snapshot=snapshot,
    )
