"""Форматирование диагностики правила МС для карточки ключа Telegram."""

from __future__ import annotations

from app.client_bot.user_interface.utils.target_place_display import (
    TargetPlaceSource,
    format_target_place_display,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.above_target_min_bid_diagnostic import (
    AboveTargetMinBidDiagnostic,
    AboveTargetMinBidDiagnosticState,
)


def _fmt_num(value: float | None, *, digits: int = 1) -> str:
    if value is None:
        return "н/д"
    return f"{value:.{digits}f}"


def _card_target_differs_from_rule(
    rule_target: int | None,
    card_target: int | None,
) -> bool:
    """True, если «Целевая позиция» карточки не совпадает с target_place ключа для МС."""
    if card_target is None:
        return False
    return rule_target != card_target


def _card_target_suffix(
    rule_target: int | None,
    card_target: int | None,
    card_source: TargetPlaceSource | None,
) -> str:
    """Пояснение, когда правило МС смотрит на ключ, а карточка — на другую цель."""
    if not _card_target_differs_from_rule(rule_target, card_target):
        return ""
    value_str, source_label = format_target_place_display(
        card_target, card_source or "default"
    )
    return f", цель карточки: {value_str} ({source_label})"


def _rule_target_label(target: int, *, card_target: int | None) -> str:
    """Подпись target в pos-gate: «на ключе», если карточка показывает другую цель."""
    if _card_target_differs_from_rule(target, card_target):
        return f"target {target} (на ключе)"
    return f"target {target}"


def _pos_min_summary(
    diag: AboveTargetMinBidDiagnostic,
    *,
    card_target: int | None = None,
    card_source: TargetPlaceSource | None = None,
) -> str:
    pos = diag.current_position
    target = diag.target_place
    cpm = diag.current_cpm
    min_bid = diag.min_bid
    parts: list[str] = []
    if pos is not None and target is not None:
        target_label = _rule_target_label(target, card_target=card_target)
        if diag.position_condition_pass:
            parts.append(f"pos {pos} < {target_label}")
        else:
            parts.append(f"pos {pos} >= {target_label}")
    if cpm is not None and min_bid is not None:
        if diag.min_bid_condition_pass:
            parts.append(f"CPM {cpm}≤{min_bid}")
        else:
            parts.append(f"CPM {cpm}>{min_bid}")
    summary = ", ".join(parts)
    suffix = _card_target_suffix(target, card_target, card_source)
    if suffix and summary:
        return f"{summary}{suffix}"
    return summary or suffix.lstrip(", ")


def _inactive_reason(
    diag: AboveTargetMinBidDiagnostic,
    *,
    card_target: int | None = None,
    card_source: TargetPlaceSource | None = None,
) -> str:
    if diag.reason_no_data:
        return diag.reason_no_data
    if diag.position_condition_pass is False:
        pos = diag.current_position
        target = diag.target_place
        if pos is not None and target is not None:
            target_label = _rule_target_label(target, card_target=card_target)
            reason = f"pos {pos} >= {target_label}"
            suffix = _card_target_suffix(target, card_target, card_source)
            return f"{reason}{suffix}" if suffix else reason
    if diag.min_bid_condition_pass is False:
        cpm = diag.current_cpm
        min_bid = diag.min_bid
        if cpm is not None and min_bid is not None:
            return f"CPM {cpm} > min {min_bid}"
    if diag.target_place is None:
        suffix = _card_target_suffix(None, card_target, card_source)
        if suffix:
            return f"нет target_place на ключе{suffix}"
        return "нет target_place"
    if diag.current_cpm is None or diag.current_cpm <= 0:
        return "нет CPM"
    return (
        _pos_min_summary(
            diag, card_target=card_target, card_source=card_source
        )
        or "условие МС не выполнено"
    )


def _format_pfo_part(diag: AboveTargetMinBidDiagnostic) -> str:
    """Фрагмент PFO для строки МС: число или «н/д»."""
    if diag.pay_for_order is None:
        return "PFO н/д"
    return f"PFO {_fmt_num(diag.pay_for_order, digits=2)}"


def _format_threshold_part(diag: AboveTargetMinBidDiagnostic) -> str:
    """Фрагмент threshold для строки МС: число или «н/д»."""
    if diag.resolved_target_cost is None:
        return "threshold н/д"
    return f"threshold {_fmt_num(diag.resolved_target_cost, digits=2)}"


def _blocked_unevaluated_cost_line(
    diag: AboveTargetMinBidDiagnostic, summary: str
) -> str:
    """BLOCKED без cost gate: раздельно PFO и threshold, без ложного «PFO н/д»."""
    pfo_part = _format_pfo_part(diag)
    threshold_part = _format_threshold_part(diag)
    gate_note = "cost gate не оценён"
    if diag.reason_no_data:
        gate_note = f"{gate_note}: {diag.reason_no_data}"
    return f"МС: выкл — {summary}, {pfo_part}, {threshold_part}, {gate_note}"


def _temporary_recheck_line(diag: AboveTargetMinBidDiagnostic, summary: str) -> str:
    """TEMPORARY_RECHECK: показать cost gate, если inputs были доступны."""
    prefix = f"МС: тест — временно включён для проверки, {summary}"
    if diag.cost_gate_evaluated:
        pfo = _fmt_num(diag.pay_for_order, digits=2)
        threshold = _fmt_num(diag.resolved_target_cost, digits=2)
        if diag.cost_condition_pass:
            return f"{prefix}, PFO {pfo}≤{threshold}"
        return f"{prefix}, PFO {pfo}>{threshold}"
    pfo_part = _format_pfo_part(diag)
    threshold_part = _format_threshold_part(diag)
    gate_note = "cost gate не оценён"
    if diag.reason_no_data:
        gate_note = f"{gate_note}: {diag.reason_no_data}"
    return f"{prefix}, {pfo_part}, {threshold_part}, {gate_note}"


def format_ms_rule_line(
    diag: AboveTargetMinBidDiagnostic | None,
    *,
    card_target_place: int | None = None,
    card_target_source: TargetPlaceSource | None = None,
) -> str:
    """Одна строка для карточки ключа: «МС: pass — pos 38 < target 71, …».

    Правило МС сравнивает позицию с ``keyword_setting.target_place`` (на ключе).
    ``card_target_place`` / ``card_target_source`` — эффективная цель из строки
    «Целевая позиция»; при расхождении добавляется пояснение «цель карточки: …».
    """
    if diag is None:
        return "МС: н/д — нет диагностики (ожидается пересчёт)"

    summary = _pos_min_summary(
        diag,
        card_target=card_target_place,
        card_source=card_target_source,
    )
    state = diag.state

    if state == AboveTargetMinBidDiagnosticState.INACTIVE:
        reason = _inactive_reason(
            diag,
            card_target=card_target_place,
            card_source=card_target_source,
        )
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
        return _blocked_unevaluated_cost_line(diag, summary)

    if state == AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK:
        return _temporary_recheck_line(diag, summary)

    if state == AboveTargetMinBidDiagnosticState.NO_DATA:
        detail = diag.reason_no_data or "нет данных для оценки МС"
        return f"МС: н/д — {detail}"

    return f"МС: н/д — неизвестное состояние ({state})"
