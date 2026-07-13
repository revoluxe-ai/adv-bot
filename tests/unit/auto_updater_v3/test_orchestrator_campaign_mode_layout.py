"""Unit: статическая проверка взаимоисключающих campaign-веток V3."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    build_normal_preamble_executors,
)

_ROOT = Path(__file__).resolve().parents[3] / "app" / "modules" / "shop_runner" / "service_manager" / "services" / "auto_updater_v3"
_ORCHESTRATOR = _ROOT / "orchestrator.py"
_DATA_MANAGER = _ROOT / "data_update_manager" / "manager.py"
_NOT_FULL_VALIDATE = _ROOT / "update_pipeline" / "executors" / "not_full_validate.py"
_EXECUTORS_INIT = _ROOT / "update_pipeline" / "executors" / "__init__.py"


def _code_without_docstrings(source: str) -> str:
    """Исключает docstring — в них намеренно упоминается legacy ``CapDownExecutor``."""
    return re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', "", source)


def _assert_no_cap_down_executor_wiring(init_src: str) -> None:
    """Legacy cap_down не импортируется и не инстанцируется (упоминание в docstring — OK)."""
    code = _code_without_docstrings(init_src)
    assert "CapDownExecutor" not in code
    assert "EligibilityCapDownExecutor" not in code
    assert "plan_mode_cap_down" not in code
    assert "eligibility_cap_down" not in code


@pytest.mark.unit
def test_no_legacy_cap_down_executor_in_preamble() -> None:
    """Legacy ``CapDownExecutor`` / ``plan_mode_cap_down`` намеренно удалены (см. V3_UPDATER_VALIDATION.md)."""
    init_src = _EXECUTORS_INIT.read_text(encoding="utf-8")
    _assert_no_cap_down_executor_wiring(init_src)
    names = [ex.phase_name for ex in build_normal_preamble_executors()]
    assert "cap_down" not in names


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
def test_operable_filter_in_data_manager_before_normal_pipeline() -> None:
    """Filter operable — в ``DataUpdateManager.load`` до NORMAL pipeline."""
    data_src = _DATA_MANAGER.read_text(encoding="utf-8")
    orch = _ORCHESTRATOR.read_text(encoding="utf-8")
    init_src = _EXECUTORS_INIT.read_text(encoding="utf-8")
    assert "filter_operable_v3_contexts" in data_src
    assert "HardStatusValidateExecutor" in init_src
    assert "NotFullValidateExecutor" in init_src
    _assert_no_cap_down_executor_wiring(init_src)
    assert "tick_report.record_filter" in data_src
    assert "prepare_v3_operable_ladder_contexts" not in data_src
    assert "prepare_v3_operable_ladder_contexts" not in orch
    assert "build_for_tick" in orch
    assert ".run_preamble(" in orch
    assert "update_ctx" in orch
    assert "trace_collector=trace_collector" in orch
