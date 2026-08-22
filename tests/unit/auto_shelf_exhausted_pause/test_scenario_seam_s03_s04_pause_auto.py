"""Scenario seams S03/S04: activity path → pause_auto (ASEP).

S03 — Exhausted epoch / no resolve-CPO fit → Auto pause (GIVEN PG our-block
already active; WB thin end only — PG latch receipt-PASS elsewhere).

S04 — Already-exhausted on reconcile/activity tick arms Auto pause without a
fresh detect/latch producer (same activity entry; must fail if only post-event
producer covered).

Does not AsyncMock production latch decision logic; state is GIVEN SoT.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    AutoReasonCode,
    CampaignActivityCommand,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    CONTRACT_ID,
    WB_PAUSE_AUTO_CASES,
    RecordingWbAutoLifecycle,
)


def _active_state(*, notify_sent: bool = True) -> SimpleNamespace:
    """PG our-block already true (no fresh latch producer)."""
    return SimpleNamespace(
        shelf_exhausted_pause_active=True,
        shelf_exhausted_notify_sent_at=(
            datetime.now(UTC) if notify_sent else None
        ),
        shelf_exhausted_resolve_cpo_kind="max",
        shelf_exhausted_resolve_cpo_value=250.0,
        shelf_exhausted_due_at=datetime.now(UTC) + timedelta(days=7),
        shelf_exhausted_epoch_pending=False,
    )


def _complex_adv() -> SimpleNamespace:
    return SimpleNamespace(
        shop_id="shop-asep",
        shop_name="Shop",
        auto_adv_id=501,
        nmids=[9001],
        main_nmid=9001,
        adv_setting=SimpleNamespace(
            id=77,
            name="Camp",
            auto_shelf_bid_control_enabled=True,
        ),
    )


def _service(
    wb: RecordingWbAutoLifecycle,
    *,
    state: SimpleNamespace,
) -> tuple[AutoAdvActiveControlService, MagicMock]:
    repo = MagicMock()
    repo.get_state = AsyncMock(return_value=state)
    repo.mark_shelf_exhausted_notify_sent = AsyncMock()
    reason_manager = MagicMock()
    reason_manager.set = AsyncMock()
    service = AutoAdvActiveControlService(
        wb_modifier=wb,  # type: ignore[arg-type]
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
        redis_campaign_activity_reason_manager=reason_manager,
        shelf_bid_control_repository=repo,
    )
    return service, reason_manager


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s03_activity_pauses_auto_when_shelf_exhausted_active() -> None:
    """S03 scenario_seam: detect/tick SoT active → pause_auto; no auction pause.

    Contract: ``asep.wb.pause_auto_lifecycle.v1``. Production entry:
    ``AutoAdvActiveControlService._maybe_apply_shelf_exhausted_pause``.
    """
    assert CONTRACT_ID == "asep.wb.pause_auto_lifecycle.v1"
    wb = RecordingWbAutoLifecycle()
    adv = _complex_adv()
    service, reason_manager = _service(wb, state=_active_state(notify_sent=True))

    blocked = await service._maybe_apply_shelf_exhausted_pause(
        adv,  # type: ignore[arg-type]
        auto_adv_id=501,
        auto_status=WBAdvActiveStatus.STARTED,
    )

    assert blocked is True
    pause_case = next(c for c in WB_PAUSE_AUTO_CASES if c.case_id == "pause_auto_allowed")
    forbidden = next(
        c for c in WB_PAUSE_AUTO_CASES if c.case_id == "pause_auction_forbidden"
    )
    start_case = next(
        c for c in WB_PAUSE_AUTO_CASES if c.case_id == "start_auto_not_on_enter"
    )
    wb.assert_matches_case(pause_case, complex_adv=adv)
    wb.assert_matches_case(forbidden)
    wb.assert_matches_case(start_case)
    reason_manager.set.assert_awaited()
    call_args = reason_manager.set.await_args
    assert call_args is not None
    assert call_args.args[0] == 501
    reason = call_args.args[2]
    assert reason.command == CampaignActivityCommand.PAUSE
    assert reason.reason_code == AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s04_reconcile_tick_arms_pause_when_already_exhausted() -> None:
    """S04 scenario_seam: GIVEN already-true exhausted; activity tick → pause_auto.

    No fresh producer/latch call — only ``get_state`` returning active SoT.
    Fails if coverage only exercises post-event detect producer without this
    activity entry.
    """
    wb = RecordingWbAutoLifecycle()
    adv = _complex_adv()
    state = _active_state(notify_sent=True)
    service, _reason = _service(wb, state=state)
    repo = service._shelf_bid_control_repository

    blocked = await service._maybe_apply_shelf_exhausted_pause(
        adv,  # type: ignore[arg-type]
        auto_adv_id=501,
        auto_status=WBAdvActiveStatus.STARTED,
    )

    assert blocked is True
    # Already-exhausted tick: read SoT only — no fresh latch producer.
    assert repo.get_state.await_count == 1  # type: ignore[union-attr]
    pause_case = next(c for c in WB_PAUSE_AUTO_CASES if c.case_id == "pause_auto_allowed")
    wb.assert_matches_case(pause_case, complex_adv=adv)
    forbidden = next(
        c for c in WB_PAUSE_AUTO_CASES if c.case_id == "pause_auction_forbidden"
    )
    wb.assert_matches_case(forbidden)
