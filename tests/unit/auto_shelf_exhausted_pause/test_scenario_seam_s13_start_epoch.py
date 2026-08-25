"""Scenario seam S13: clear-only-our-block → start_auto + mark epoch started."""

from __future__ import annotations

import pytest

from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_shelf_exhausted_pause.asep_activity_helpers import (
    make_state,
    run_ensure_with_shelf_state,
)
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    CONTRACT_ID,
    WB_PAUSE_AUTO_CASES,
    RecordingWbAutoLifecycle,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s13_start_auto_and_open_epoch_when_only_our_block_cleared() -> None:
    """S13: no other blockers + epoch_pending → start_auto + mark epoch.

    Combined activity seam (not PG-only fragments).
    """
    assert CONTRACT_ID == "asep.wb.pause_auto_lifecycle.v1"
    wb = RecordingWbAutoLifecycle()
    reason = await run_ensure_with_shelf_state(
        wb=wb,
        state=make_state(pause_active=False, epoch_pending=True),
        auto_status=WBAdvActiveStatus.PAUSE,
        spend_today=10.0,
        auto_budget_daily_limit=1000,
    )
    start_case = next(
        c
        for c in WB_PAUSE_AUTO_CASES
        if c.case_id == "start_auto_after_clear_only_our_block"
    )
    wb.assert_matches_case(start_case)
    assert "pause_auto_campaign" not in wb.methods_called()
    repo = reason.shelf_repo  # type: ignore[attr-defined]
    repo.mark_shelf_exhausted_epoch_started.assert_awaited_once()
