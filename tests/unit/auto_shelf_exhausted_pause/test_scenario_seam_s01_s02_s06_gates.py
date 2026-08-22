"""Scenario seams S01/S02/S06: gate / still-have-bids — no latch, no pause_auto."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from tests.unit.auto_shelf_exhausted_pause.asep_manager_tick_fixtures import (
    build_tick_fixture,
)
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    WB_PAUSE_AUTO_CASES,
    RecordingWbAutoLifecycle,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s01_module_off_tick_no_latch_no_pause_auto() -> None:
    """S01: shelves OFF → production tick MUST NOT latch; WB pause silent."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            module_enabled=False,
            next_test_bid_minor=None,
        )
    )
    wb = RecordingWbAutoLifecycle()

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    repository.latch_shelf_exhausted_pause.assert_not_awaited()
    repository.clear_shelf_exhausted_pause.assert_not_awaited()
    assert wb.methods_called() == []
    forbidden = next(
        c for c in WB_PAUSE_AUTO_CASES if c.case_id == "pause_auction_forbidden"
    )
    wb.assert_matches_case(forbidden)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s02_non_best_strategy_tick_no_latch() -> None:
    """S02: shelves ON + CPC (non-Best) → terminal path no-op; no latch/pause."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            module_enabled=True,
            strategy=AutoShelfBidControlStrategy.CPC,
            next_test_bid_minor=None,
        )
    )
    wb = RecordingWbAutoLifecycle()

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    repository.latch_shelf_exhausted_pause.assert_not_awaited()
    assert wb.methods_called() == []
    assert complex_adv.auto_shelf_bid_control_strategy == AutoShelfBidControlStrategy.CPC


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s06_still_have_bids_to_test_no_terminal_latch() -> None:
    """S06: next_test_bid present → no latch and no pause_auto on production tick."""
    manager, repository, state, settings_obj, complex_adv, snapshot = (
        build_tick_fixture(
            module_enabled=True,
            strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
            next_test_bid_minor=16_000,  # still have bids to test
        )
    )
    wb = RecordingWbAutoLifecycle()

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    repository.latch_shelf_exhausted_pause.assert_not_awaited()
    assert snapshot.fresh_next_test_bid_minor == 16_000
    assert wb.methods_called() == []
