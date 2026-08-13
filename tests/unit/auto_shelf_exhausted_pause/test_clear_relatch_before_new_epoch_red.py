"""RED regression: clear must not re-latch before a new Auto testing epoch.

Bug ROOT-001 / BUGCASE-ASEP-CLEAR-RELATCH:
``clear_shelf_exhausted_pause`` sets ``shelf_exhausted_epoch_pending=True`` and
clears the PG our-block, but the next shelf tick still treats the old exhausted
epoch as terminal (``next_test_bid`` empty) and re-latches because detect /
``apply_shelf_exhausted_tick`` ignore ``epoch_pending``.

Invariant: after calendar / plan-fit / manual clear, while ``epoch_pending`` is
True and a new Auto testing epoch has not started, the next tick MUST NOT call
``latch_shelf_exhausted_pause``.
"""

from __future__ import annotations

# pyright: reportPrivateUsage=false

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tests.unit.auto_shelf_exhausted_pause.asep_manager_tick_fixtures import (
    _NOW,
    build_tick_fixture,
    qualified_fit_cycle_stats,
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calendar_clear_next_tick_does_not_relatch_while_epoch_pending() -> None:
    """Calendar clear → epoch_pending; next tick must not re-latch old empty epoch."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            block_active=True,
            due_at=_NOW.replace(year=2020),  # calendar due
            next_test_bid_minor=None,  # old epoch still empty
            cycle_stats=[],
            plan_ranked=[{"bid": 15_000, "cpo_rub": 999.0}],  # no plan-fit
        )
    )
    state.shelf_exhausted_epoch_pending = False
    state.shelf_exhausted_notify_sent_at = _NOW - timedelta(hours=1)
    repository.clear_shelf_exhausted_pause = AsyncMock(
        side_effect=_apply_clear_side_effect(state)
    )
    repository.get_state = AsyncMock(return_value=state)

    # Tick 1: calendar clear our-block + set epoch_pending (production clear).
    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )
    repository.clear_shelf_exhausted_pause.assert_awaited_once()
    assert state.shelf_exhausted_pause_active is False
    assert state.shelf_exhausted_epoch_pending is True
    repository.latch_shelf_exhausted_pause.assert_not_awaited()

    # Tick 2: same empty next_test_bid, still awaiting new Auto epoch.
    repository.latch_shelf_exhausted_pause.reset_mock()
    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    # Causal claim ROOT-001: epoch_pending must suppress re-latch until real
    # Auto start opens a new testing epoch (clear alone ≠ new cycle).
    repository.latch_shelf_exhausted_pause.assert_not_awaited()
    assert state.shelf_exhausted_pause_active is False
    assert state.shelf_exhausted_epoch_pending is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plan_fit_clear_next_tick_does_not_relatch_while_epoch_pending() -> None:
    """Plan-fit clear → epoch_pending; next tick must not re-latch old empty epoch."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            block_active=True,
            due_at=_NOW + timedelta(days=3),  # future due → plan-fit path wins
            next_test_bid_minor=None,
            cycle_stats=qualified_fit_cycle_stats(),
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

    # After clear, remove plan-fit so detect would otherwise latch (empty bids).
    snapshot.rec_bid_recommendation = {
        "plan_ranked": [{"bid": 15_000, "cpo_rub": 999.0}]
    }
    # Empty qualified set on next tick (no new testing coverage yet).
    repository.latch_shelf_exhausted_pause.reset_mock()
    analytics = manager._analytics
    analytics.get_bid_stats = AsyncMock(return_value=[])

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    repository.latch_shelf_exhausted_pause.assert_not_awaited()
    assert state.shelf_exhausted_epoch_pending is True
