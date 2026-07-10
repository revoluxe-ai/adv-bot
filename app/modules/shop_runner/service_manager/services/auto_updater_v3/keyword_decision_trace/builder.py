"""Сборка ``KeywordDecisionTraceSnapshot`` из collector после preamble."""

from __future__ import annotations

from datetime import datetime

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.collector import (
    KeywordAccumulator,
    KeywordDecisionTraceCollector,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceSnapshot,
    KeywordDecisionTraceStep,
    TraceStepStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.status_resolver import (
    resolve_state_label,
    resolve_status_hint,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.executor_phase_map import (
    title_ru_for_phase,
    phase_id_for_executor,
)


def build_keyword_decision_trace_snapshot(
    collector: KeywordDecisionTraceCollector,
    *,
    adv_id: int,
    tick_finished_at: datetime,
    nmids: list[int] | None = None,
) -> KeywordDecisionTraceSnapshot:
    """Построить snapshot для всех operable keywords тика.

    Args:
        collector: Заполненный observer preamble.
        adv_id: ID рекламной кампании.
        tick_finished_at: Wall-clock окончания preamble.
        nmids: Артикулы кампании для entry/snapshot.

    Returns:
        Snapshot с ``len(entries) == operable_keywords``.
    """
    tick_started = collector.tick_started_at or tick_finished_at
    processing_started = collector.processing_started_at or tick_started
    campaign_nmids = list(nmids or [])
    nmid_display = ", ".join(str(n) for n in campaign_nmids) if campaign_nmids else "—"

    entries = [
        _finalize_entry(acc, nmid_display=nmid_display, nmids=campaign_nmids)
        for acc in collector.iter_accumulators()
    ]
    operable = len(entries)

    return KeywordDecisionTraceSnapshot(
        tick_started_at=tick_started,
        processing_started_at=processing_started,
        tick_finished_at=tick_finished_at,
        tick_at=tick_finished_at,
        adv_id=adv_id,
        operable_keywords=operable,
        nmids=campaign_nmids,
        entries=entries,
    )


def _finalize_entry(
    acc: KeywordAccumulator,
    *,
    nmid_display: str,
    nmids: list[int],
) -> KeywordDecisionTraceEntry:
    dto = acc.dto
    state_after = resolve_state_label(dto)
    status_hint_after = resolve_status_hint(dto)
    data_tier = dto.data_tier.value

    net_changed = (
        acc.state_before != state_after
        or acc.target_place_before != dto.current_target_place
    )

    decisive_step, decisive_executor, decisive_reason = _resolve_decisive(acc.steps)
    final_decision_ru = _final_decision_ru(
        acc,
        state_after=state_after,
        net_changed=net_changed,
        decisive_step=decisive_step,
    )

    return KeywordDecisionTraceEntry(
        keyword_setting_id=dto.keyword_setting_id,
        keyword_text=acc.keyword_text,
        nmids=list(nmids),
        nmid_display=nmid_display,
        processing_started=True,
        processing_started_at=acc.processing_started_at,
        status_hint_before=acc.status_hint_before,
        state_before=acc.state_before,
        status_hint_after=status_hint_after,
        state_after=state_after,
        data_tier=data_tier,
        steps=acc.steps,
        final_decision_ru=final_decision_ru,
        decisive_executor=decisive_executor,
        decisive_reason_ru=decisive_reason,
        net_changed=net_changed,
    )


def _resolve_decisive(
    steps: list[KeywordDecisionTraceStep],
) -> tuple[KeywordDecisionTraceStep | None, str | None, str | None]:
    decisive: KeywordDecisionTraceStep | None = None
    for step in steps:
        if step.status in (TraceStepStatus.APPLY, TraceStepStatus.BLOCK):
            decisive = step
    if decisive is None:
        return None, None, None
    title = title_ru_for_phase(phase_id_for_executor(decisive.executor_name))
    executor_line = f"{title} ({decisive.executor_name})"
    return decisive, executor_line, decisive.reason_ru


def _final_decision_ru(
    acc: KeywordAccumulator,
    *,
    state_after: str,
    net_changed: bool,
    decisive_step: KeywordDecisionTraceStep | None,
) -> str:
    if not net_changed:
        return "Без изменений (ключ обрабатывался)"
    if state_after == "OFF":
        return "Оставить OFF"
    if acc.state_before in ("OFF", "GAP") and state_after not in ("OFF", "GAP"):
        return f"Включить {state_after}"
    if decisive_step is not None:
        return f"Итог: {decisive_step.decision_ru}"
    return f"Итог: {acc.state_before}→{state_after}"
