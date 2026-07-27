"""Regression: CardAbHold interrupt пропускает apply и finally TP sync."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
)

_ORCH = "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator"
_DM = "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager"
_INTERRUPT = f"{_ORCH}.abort_ordinary_v3_if_enter_signaled"


def _tick_data(*, mode: CampaignMode = CampaignMode.NORMAL) -> MagicMock:
    """Минимальный TickData-stub для orchestrator after-load path."""
    tick = MagicMock()
    tick.campaign_mode = mode
    tick.dto = MagicMock()
    tick.tick_input = MagicMock()
    tick.tick_input.calibration_phase_extra = {}
    tick.tick_input.campaign_orders_per_cart_7d = None
    tick.tick_report_ready = False
    tick.contexts = []
    tick.all_contexts = []
    tick.ledger = MagicMock()
    tick.raw_profiles = {}
    tick.ladder_inputs = None
    tick.eligibility_by_ks_id = {}
    tick.sync_fallback_by_id = None
    tick.sales_state = None
    tick.complex_adv = MagicMock()
    return tick


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_ab_hold_abort_skips_apply_and_finally_sync() -> None:
    """Blocked: interrupt после load → ни apply, ни sync_target_places в finally.

    Spec: Enter interrupts unsafe concurrent structural apply — structural
    write boundary включает и apply, и finally TP sync.
    """
    complex_adv = MagicMock()
    complex_adv.adv_id = 77
    complex_adv.adv_setting = MagicMock()
    complex_adv.auto_add_only_relevant_phrase = False
    complex_adv.get_keywords = AsyncMock(return_value=[])

    apply_instance = MagicMock()
    apply_instance.apply = AsyncMock()
    apply_instance.sync_target_places_if_needed = AsyncMock(return_value=False)

    with (
        patch(
            f"{_DM}.DataUpdateManager.load",
            new=AsyncMock(return_value=_tick_data()),
        ),
        patch(_INTERRUPT, new=AsyncMock(return_value=True)),
        patch(f"{_ORCH}.ApplyManager", return_value=apply_instance),
    ):
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    apply_instance.apply.assert_not_awaited()
    apply_instance.sync_target_places_if_needed.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_without_abort_still_syncs_target_places() -> None:
    """Allowed: без interrupt finally sync по-прежнему вызывается."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 78
    complex_adv.adv_setting = MagicMock()
    complex_adv.auto_add_only_relevant_phrase = False
    complex_adv.get_keywords = AsyncMock(return_value=[])

    apply_instance = MagicMock()
    apply_instance.apply = AsyncMock()
    apply_instance.sync_target_places_if_needed = AsyncMock(return_value=True)

    pipeline = MagicMock()
    pipeline.update_context = MagicMock(
        adv_state=MagicMock(calibration_phase_extra={}),
        keywords=[],
    )
    pipeline.contexts = []
    pipeline.all_contexts = []
    pipeline.ladder_inputs = None
    pipeline.eligibility = {}
    pipeline.calibration_executed = False

    with (
        patch(
            f"{_DM}.DataUpdateManager.load",
            new=AsyncMock(return_value=_tick_data()),
        ),
        patch(_INTERRUPT, new=AsyncMock(return_value=False)),
        patch(f"{_ORCH}.ApplyManager", return_value=apply_instance),
        patch(
            f"{_ORCH}.UpdateContextManager.build_for_tick",
            return_value=MagicMock(),
        ),
        patch(
            f"{_ORCH}.UpdatePipelineManager.run_preamble",
            return_value=pipeline,
        ),
        patch(f"{_ORCH}.needs_apply_manager", return_value=True),
        patch(f"{_ORCH}.is_campaign_full_stop", return_value=False),
    ):
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    apply_instance.apply.assert_awaited()
    apply_instance.sync_target_places_if_needed.assert_awaited()
