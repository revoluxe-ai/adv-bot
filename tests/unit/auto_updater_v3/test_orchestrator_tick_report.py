"""Unit: orchestrator persists V3TickReport snapshot."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3TickReportSnapshot,
)


def _patch_process_adv_v3_normal(persist_mock: AsyncMock) -> dict[str, object]:
    """Словарь patch targets для укороченного NORMAL-тика."""
    pfc = MagicMock()
    pfc.check_equal_in_cache = AsyncMock(return_value=False)
    pfc.set_new_plan_fact = AsyncMock()
    views = MagicMock()
    views.get_cached_views = AsyncMock(return_value=50)
    views.set_views = AsyncMock()
    step = MagicMock()
    step.get_state = AsyncMock(return_value=None)
    step.set_state = AsyncMock()
    return {
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context": AsyncMock(
            return_value=(MagicMock(), {})
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts": lambda *a, **k: [],
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data": lambda *a, **k: MagicMock(
            orders=10,
            target_pay_for_order=80.0,
            max_pay_for_order=100.0,
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_v3_fact_data": AsyncMock(
            return_value=(
                MagicMock(predict_orders=10.0, pay_for_order=85.0, original_orders=10),
                "dto",
            )
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state": lambda *a, **k: SalesStates.STABLE,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode.resolve_campaign_mode": lambda *a, **k: CampaignMode.NORMAL,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode.is_campaign_full_stop": lambda *a, **k: False,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode.allows_ladder_phases": lambda *a, **k: True,
        "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_campaign_orders_per_cart_7d": AsyncMock(
            return_value=None
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold.is_resolve_valid": lambda *a, **k: True,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold.compute_resolve_cost_threshold": lambda *a, **k: 90.0,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute": lambda *a, **k: None,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable.PayForOrderGapEnableExecutor.execute": lambda *a, **k: None,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend.PayForOrderOverMaxOffOnDeepOverspendExecutor.execute": lambda *a, **k: None,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.ResolveCalibrationExecutor.execute": lambda *a, **k: None,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact": lambda *a, **k: pfc,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews": lambda *a, **k: views,
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views": AsyncMock(
            return_value=100
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState": lambda *a, **k: step,
        "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rec_orders_per_view_for_v3": AsyncMock(
            return_value=None
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.tick_context.refresh_v3_tick_state": lambda *a, **k: (
            [],
            {},
            MagicMock(),
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions": lambda *a, **k: [],
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db": AsyncMock(
            return_value=False
        ),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.persist_v3_keyword_changes": AsyncMock(),
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.persist_v3_tick_report": persist_mock,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_persists_tick_report_on_normal_tick() -> None:
    """При NORMAL preamble snapshot пишется в Redis."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
        process_adv_v3,
    )

    complex_adv = MagicMock()
    complex_adv.adv_id = 55
    complex_adv.shop_id = 1
    complex_adv.adv_setting = MagicMock()
    complex_adv.adv_setting.adv_id = 55
    complex_adv.adv_setting.name = "Test"
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.rec_system_promotion_mode_active = False
    complex_adv.get_keywords = AsyncMock(return_value=[])

    persist_mock = AsyncMock()
    patches = _patch_process_adv_v3_normal(persist_mock)
    patchers = [patch(target, new=val) for target, val in patches.items()]
    for p in patchers:
        p.start()
    try:
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())
    finally:
        for p in patchers:
            p.stop()

    persist_mock.assert_awaited_once()
    snapshot = persist_mock.call_args[0][1]
    assert isinstance(snapshot, V3TickReportSnapshot)
    assert snapshot.campaign_mode == "NORMAL"
    assert any(p.phase_id == "filter" for p in snapshot.phases)
    nf_phase = next(
        p for p in snapshot.phases if p.phase_id == "not_full_target_place_plan_fact"
    )
    assert nf_phase.executed
