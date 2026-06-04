"""Unit: диагностика нулевого исхода preamble-фаз для V3 tick report."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_phase_notes import (
    summarize_phase_zero_actions,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


@pytest.mark.unit
def test_enable_gap_fact_above_stabilization_zone() -> None:
    resolve = 550.0
    fact = MAX_PAY_STABILIZATION_RATIO * resolve + 1.0
    note = summarize_phase_zero_actions(
        "pay_for_order_gap_enable",
        prepared=[],
        fact_pay_for_order=fact,
        resolve=resolve,
    )
    assert "0.9" in note or "90%" in note or "стабилизации" in note


@pytest.mark.unit
def test_enable_gap_fact_above_max() -> None:
    note = summarize_phase_zero_actions(
        "pay_for_order_gap_enable",
        prepared=[],
        fact_pay_for_order=600.0,
        resolve=550.0,
        max_pay_for_order=550.0,
    )
    assert "max" in note


@pytest.mark.unit
def test_enable_gap_no_candidates_without_eligibility() -> None:
    note = summarize_phase_zero_actions(
        "pay_for_order_gap_enable",
        prepared=[],
        fact_pay_for_order=100.0,
        resolve=550.0,
        eligibility_by_ks_id=None,
    )
    assert "GAP" in note or "NO DATA" in note


@pytest.mark.unit
def test_calibration_loosen_empty_prepared() -> None:
    note = summarize_phase_zero_actions(
        "resolve_calibration",
        prepared=[],
        resolve=550.0,
        calibration_direct=CalibrationDirect.LOOSEN,
    )
    assert "следующим шагом UP" in note


@pytest.mark.unit
def test_calibration_loosen_operable_at_ceiling() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

    kw = _calc_kw(
        ks_id=1,
        text="kw",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        hard_status=1,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=[])
    prepared = build_prepared_from_contexts([ctx])
    note = summarize_phase_zero_actions(
        "resolve_calibration",
        prepared=prepared,
        resolve=550.0,
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=1,
    )
    assert "следующим шагом UP" in note
