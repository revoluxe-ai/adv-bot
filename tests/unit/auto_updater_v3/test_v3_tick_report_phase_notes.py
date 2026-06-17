"""Unit: диагностика нулевого исхода preamble-фаз для V3 tick report."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    gap_enable_plan_headroom_floor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_phase_notes import (
    summarize_phase_zero_actions,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


@pytest.mark.unit
def test_enable_gap_fact_above_plan_max_stabilization_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates.gap_enable_plan_headroom_ratio",
        lambda: 0.9,
    )
    max_cpo = 550.0
    resolve = 200.0
    fact = gap_enable_plan_headroom_floor(max_cpo) + 0.01
    note = summarize_phase_zero_actions(
        "pay_for_order_gap_enable",
        prepared=[],
        fact_pay_for_order=fact,
        resolve=resolve,
        max_pay_for_order=max_cpo,
    )
    assert "plan.max" in note


@pytest.mark.unit
def test_pfo_off_skip_when_fact_lt_plan_headroom_ratio() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
        plan_max_stabilization_floor,
    )

    max_cpo = 100.0
    fact = plan_max_stabilization_floor(max_cpo) - 0.01
    note = summarize_phase_zero_actions(
        "pay_for_order_over_max_off_on_deep_overspend",
        prepared=[],
        fact_pay_for_order=fact,
        max_pay_for_order=max_cpo,
    )
    assert "plan.max" in note


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
    assert "overspend, enable не нужен" not in note


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


@pytest.mark.unit
def test_resolve_clamp_zero_actions_reports_neutral_reason() -> None:
    kw = _calc_kw(
        ks_id=1,
        text="kw",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts([KeywordV3Context(keyword=kw, position_profile=[])])
    note = summarize_phase_zero_actions(
        "clamp_states_to_resolve_when_no_effective_steps",
        prepared=prepared,
        resolve=550.0,
        max_effective_steps=1,
    )
    assert "effective steps включены" not in note
    assert "изменений по resolve не требуется" in note
