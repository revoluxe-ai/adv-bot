"""Unit: статическая проверка взаимоисключающих campaign-веток V3."""

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3] / "app" / "modules" / "shop_runner" / "service_manager" / "services" / "auto_updater_v3"
_ORCHESTRATOR = _ROOT / "orchestrator.py"
_DATA_MANAGER = _ROOT / "data_update_manager" / "manager.py"
_NOT_FULL_VALIDATE = _ROOT / "update_pipeline" / "executors" / "not_full_validate.py"


@pytest.mark.unit
def test_validate_not_full_in_pipeline_not_orchestrator() -> None:
    """``NotFullValidateExecutor`` в pipeline, не в orchestrator."""
    orch = _ORCHESTRATOR.read_text(encoding="utf-8")
    nf = _NOT_FULL_VALIDATE.read_text(encoding="utf-8")
    assert "plan_mode_cap_down(" not in orch
    assert "NotFullValidateExecutor" in nf
    assert "validate_not_full_state" in nf
    assert "UpdatePipelineManager" in orch
    assert "elif tick_data.campaign_mode == CampaignMode.NORMAL" in orch


@pytest.mark.unit
def test_operable_sync_in_data_manager_before_normal_pipeline() -> None:
    """Filter/sync operable — в ``DataUpdateManager.load`` до NORMAL pipeline."""
    data_src = _DATA_MANAGER.read_text(encoding="utf-8")
    orch = _ORCHESTRATOR.read_text(encoding="utf-8")
    assert "prepare_v3_operable_ladder_contexts" in data_src
    assert "tick_report.record_filter" in data_src
    assert "prepare_v3_operable_ladder_contexts" not in orch
    assert "build_for_tick" in orch
    assert ".run_preamble(update_ctx)" in orch
