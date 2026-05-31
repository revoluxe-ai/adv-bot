"""Форматирование диагностики правила МС для карточки ключа Telegram."""

from __future__ import annotations

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.above_target_min_bid_diagnostic import (
    AboveTargetMinBidDiagnostic,
    AboveTargetMinBidDiagnosticState,
)


def _fmt_num(value: float | None, *, digits: int = 1) -> str:
    if value is None:
        return "н/д"
    return f"{value:.{digits}f}"


def _pos_min_summary(diag: AboveTargetMinBidDiagnostic) -> str:
    pos = diag.current_position
    target = diag.target_place
    cpm = diag.current_cpm
    min_bid = diag.min_bid
    parts: list[str] = []
    if pos is not None and target is not None:
        if diag.position_condition_pass:
            parts.append(f"pos {pos} < target {target}")
        else:
            parts.append(f"pos {pos} >= target {target}")
    if cpm is not None and min_bid is not None:
        if diag.min_bid_condition_pass:
            parts.append(f"CPM {cpm}≤{min_bid}")
        else:
            parts.append(f"CPM {cpm}>{min_bid}")
    return ", ".join(parts)


def _inactive_reason(diag: AboveTargetMinBidDiagnostic) -> str:
    if diag.reason_no_data:
        return diag.reason_no_data
    if diag.position_condition_pass is False:
        pos = diag.current_position
        target = diag.target_place
        if pos is not None and target is not None:
            return f"pos {pos} >= target {target}"
    if diag.min_bid_condition_pass is False:
        cpm = diag.current_cpm
        min_bid = diag.min_bid
        if cpm is not None and min_bid is not None:
            return f"CPM {cpm} > min {min_bid}"
    if diag.target_place is None:
        return "нет target_place"
    if diag.current_cpm is None or diag.current_cpm <= 0:
        return "нет CPM"
    return _pos_min_summary(diag) or "условие МС не выполнено"


def format_ms_rule_line(diag: AboveTargetMinBidDiagnostic | None) -> str:
    """Одна строка для карточки ключа: «МС: pass — pos 38 < target 71, …»."""
    if diag is None:
        return "МС: н/д — нет диагностики (ожидается пересчёт)"

    summary = _pos_min_summary(diag)
    state = diag.state

    if state == AboveTargetMinBidDiagnosticState.INACTIVE:
        reason = _inactive_reason(diag)
        return f"МС: нет — {reason}"

    if state == AboveTargetMinBidDiagnosticState.PASS_BY_COST:
        pfo = _fmt_num(diag.pay_for_order, digits=2)
        threshold = _fmt_num(diag.resolved_target_cost, digits=2)
        return f"МС: pass — {summary}, PFO {pfo}≤{threshold}"

    if state == AboveTargetMinBidDiagnosticState.BLOCKED:
        if diag.cost_gate_evaluated:
            pfo = _fmt_num(diag.pay_for_order, digits=2)
            threshold = _fmt_num(diag.resolved_target_cost, digits=2)
            return f"МС: выкл — {summary}, PFO {pfo}>{threshold}"
        return f"МС: выкл — {summary}, PFO н/д, cost gate не оценён"

    if state == AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK:
        return f"МС: тест — временно включён для проверки, {summary}"

    if state == AboveTargetMinBidDiagnosticState.NO_DATA:
        detail = diag.reason_no_data or "нет данных для оценки МС"
        return f"МС: н/д — {detail}"

    return f"МС: н/д — неизвестное состояние ({state})"
