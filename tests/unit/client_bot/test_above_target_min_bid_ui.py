"""Unit-тесты форматирования диагностики МС для карточки ключа."""

from __future__ import annotations

from app.client_bot.user_interface.views.above_target_min_bid_ui import format_ms_rule_line
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.above_target_min_bid_diagnostic import (
    AboveTargetMinBidDiagnostic,
    AboveTargetMinBidDiagnosticState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)


def _diag(**kwargs: object) -> AboveTargetMinBidDiagnostic:
    defaults: dict[str, object] = {
        "state": AboveTargetMinBidDiagnosticState.INACTIVE,
        "current_position": 38,
        "target_place": 71,
        "position_condition_pass": True,
        "current_cpm": 510,
        "min_bid": 510,
        "min_bid_condition_pass": True,
        "pay_for_order": 74.0,
        "resolved_target_cost": 550.0,
        "cost_gate_evaluated": False,
        "cost_condition_pass": None,
        "resulting_status": KeywordStatus.GOOD,
        "resulting_reason": KeywordStatusReason.WHITE_LIST,
    }
    defaults.update(kwargs)
    return AboveTargetMinBidDiagnostic(**defaults)  # type: ignore[arg-type]


def test_format_ms_rule_line_none() -> None:
    line = format_ms_rule_line(None)
    assert line.startswith("МС: н/д")
    assert "пересчёт" in line


def test_format_ms_rule_line_inactive() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.INACTIVE,
            position_condition_pass=False,
            current_position=80,
            target_place=71,
        )
    )
    assert line.startswith("МС: нет")


def test_format_ms_rule_line_pass_by_cost() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.PASS_BY_COST,
            cost_gate_evaluated=True,
            cost_condition_pass=True,
        )
    )
    assert line.startswith("МС: pass")
    assert "38" in line and "71" in line
    assert "510" in line
    assert "74" in line and "550" in line


def test_format_ms_rule_line_blocked_with_cost_gate() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.BLOCKED,
            pay_for_order=900.0,
            cost_gate_evaluated=True,
            cost_condition_pass=False,
            resulting_status=KeywordStatus.BAD,
            resulting_reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
        )
    )
    assert line.startswith("МС: выкл")
    assert "900" in line and "550" in line
    assert ">" in line


def test_format_ms_rule_line_blocked_without_cost_gate_missing_pfo() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.BLOCKED,
            pay_for_order=None,
            resolved_target_cost=550.0,
            cost_gate_evaluated=False,
            reason_no_data="нет PFO",
            resulting_status=KeywordStatus.BAD,
            resulting_reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
        )
    )
    assert line.startswith("МС: выкл")
    assert "PFO н/д" in line
    assert "550" in line
    assert "threshold н/д" not in line
    assert "cost gate не оценён: нет PFO" in line
    assert ">" not in line


def test_format_ms_rule_line_blocked_without_cost_gate_missing_threshold() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.BLOCKED,
            pay_for_order=900.0,
            resolved_target_cost=None,
            cost_gate_evaluated=False,
            reason_no_data="нет threshold",
            resulting_status=KeywordStatus.BAD,
            resulting_reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
        )
    )
    assert line.startswith("МС: выкл")
    assert "PFO 900" in line
    assert "PFO н/д" not in line
    assert "threshold н/д" in line
    assert "cost gate не оценён: нет threshold" in line
    assert ">" not in line


def test_format_ms_rule_line_blocked_without_cost_gate_both_missing() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.BLOCKED,
            pay_for_order=None,
            resolved_target_cost=None,
            cost_gate_evaluated=False,
            reason_no_data="нет PFO",
            resulting_status=KeywordStatus.BAD,
            resulting_reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
        )
    )
    assert line.startswith("МС: выкл")
    assert "PFO н/д" in line
    assert "threshold н/д" in line
    assert "cost gate не оценён" in line
    assert ">" not in line


def test_format_ms_rule_line_temporary_recheck_with_cost_gate_pass() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK,
            pay_for_order=74.0,
            resolved_target_cost=550.0,
            cost_gate_evaluated=True,
            cost_condition_pass=True,
            cooldown_display_tag="Т",
        )
    )
    assert line.startswith("МС: тест")
    assert "74" in line and "550" in line
    assert "≤" in line
    assert ">" not in line.split("PFO")[-1]


def test_format_ms_rule_line_temporary_recheck_with_cost_gate() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK,
            pay_for_order=900.0,
            resolved_target_cost=550.0,
            cost_gate_evaluated=True,
            cost_condition_pass=False,
            cooldown_display_tag="Т",
        )
    )
    assert line.startswith("МС: тест")
    assert "временно включён" in line
    assert "900" in line and "550" in line
    assert ">" in line


def test_format_ms_rule_line_temporary_recheck_missing_threshold() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK,
            pay_for_order=900.0,
            resolved_target_cost=None,
            cost_gate_evaluated=False,
            reason_no_data="нет threshold",
            cooldown_display_tag="Т",
        )
    )
    assert line.startswith("МС: тест")
    assert "PFO 900" in line
    assert "threshold н/д" in line
    assert "cost gate не оценён: нет threshold" in line
    assert ">" not in line


def test_format_ms_rule_line_temporary_recheck_basic() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK,
            cooldown_display_tag="Т",
            cost_gate_evaluated=True,
            cost_condition_pass=False,
            pay_for_order=900.0,
            resolved_target_cost=550.0,
        )
    )
    assert line.startswith("МС: тест")
    assert "временно включён" in line


def test_format_ms_rule_line_no_data() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.NO_DATA,
            reason_no_data="нет мин. ставки WB",
        )
    )
    assert line.startswith("МС: н/д")
    assert "мин. ставки WB" in line
    assert "cooldown_map" not in line


def test_format_ms_rule_line_prod_like_korea() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.PASS_BY_COST,
            cost_gate_evaluated=True,
            cost_condition_pass=True,
        )
    )
    assert line.startswith("МС: pass")
    assert "pos 38 < target 71" in line
    assert "CPM 510≤510" in line


def test_format_ms_rule_line_card_target_differs_from_rule() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.PASS_BY_COST,
            cost_gate_evaluated=True,
            cost_condition_pass=True,
            target_place=71,
        ),
        card_target_place=50,
        card_target_source="campaign",
    )
    assert "target 71 (на ключе)" in line
    assert "цель карточки: 50 (по кампании)" in line
    assert "pos 38 < target 71," not in line


def test_format_ms_rule_line_inactive_no_target_before_cpm_check() -> None:
    """Без target на ключе правило не доходит до min-bid gate — не показываем CPM > min."""
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.INACTIVE,
            target_place=None,
            position_condition_pass=None,
            min_bid_condition_pass=False,
            current_cpm=600,
            min_bid=510,
        )
    )
    assert line.startswith("МС: нет")
    assert "нет target_place" in line
    assert "CPM" not in line


def test_format_ms_rule_line_inactive_no_keyword_target_card_shows_campaign() -> None:
    line = format_ms_rule_line(
        _diag(
            state=AboveTargetMinBidDiagnosticState.INACTIVE,
            target_place=None,
            position_condition_pass=None,
        ),
        card_target_place=50,
        card_target_source="campaign",
    )
    assert line.startswith("МС: нет")
    assert "нет target_place на ключе" in line
    assert "цель карточки: 50 (по кампании)" in line
