"""Pure formatter экрана KeywordDecisionTrace (без I/O, Telegram limits)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.client_bot.const import MAX_MESSAGE_LENGTH
from app.client_bot.user_interface.services.keyword_decision_trace_loader import (
    KeywordDecisionTraceViewData,
    ProcessingOutcome,
    TracePresence,
)
from app.client_bot.user_interface.views.keyword_v3_profile_ui import (
    NON_V3_DECISION_TRACE_MESSAGE,
    DECISION_ACTION_LABEL,
    REASON_NOT_IN_JOURNAL,
    escape_markdown_v1,
    format_decisive_step_body,
    keyword_v3_decision_trace_button_label,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceStep,
    TraceStepStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.executor_phase_map import (
    phase_id_for_executor,
    short_label_for_executor,
    title_ru_for_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordStepRecord,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)

_MSK_TZ = timezone(timedelta(hours=3))
_TICK_TIME_FMT = "%H:%M:%S %d-%m-%Y"
_FORBIDDEN_UI_TOKENS = ("CPM", "pay_for_order", "лестниц", " CH ", "PFC")
_TRUNCATE_HEAD = 6
_TRUNCATE_TAIL = 4


def format_keyword_decision_trace_screen(view: KeywordDecisionTraceViewData) -> str:
    """Собрать Markdown-текст экрана из ViewData.

    Args:
        view: Данные из ``load_keyword_decision_trace_view``.

    Returns:
        Текст для ``ParseMode.MARKDOWN`` (legacy V1), len <= 4096.
    """
    if view.source == "non_v3":
        return NON_V3_DECISION_TRACE_MESSAGE

    safe_nmid = escape_markdown_v1(view.nmid_display)
    safe_keyword = escape_markdown_v1(view.keyword_text.replace("\n", " ").strip())
    status_label = _display_status_label(view.display_status)

    lines = [
        "🔎 *Почему бот так решил?*",
        "",
        f"📦 {safe_nmid}",
        f"🔑 {safe_keyword}",
        f"🔄 Текущий статус: {status_label}",
        "",
    ]
    lines.extend(_timing_lines(view))
    lines.append("")
    lines.extend(_processing_state_lines(view))

    if view.source == "trace" and view.entry is not None:
        lines.append("")
        lines.append("Каскад решений:")
        lines.extend(_cascade_lines(view.entry.steps, compact=False))
        lines.append("")
        lines.extend(_summary_lines(view.entry))
    elif view.source == "legacy_changes" and view.legacy_decisive is not None:
        lines.append("")
        lines.append("Последнее записанное решение V3 (legacy journal):")
        lines.extend(_legacy_decisive_lines(view.legacy_decisive, view.legacy_tick_at))

    text = "\n".join(lines)
    if len(text) <= MAX_MESSAGE_LENGTH:
        return text

    if view.source == "trace" and view.entry is not None:
        compact_lines = [
            "🔎 *Почему бот так решил?*",
            "",
            f"📦 {safe_nmid}",
            f"🔑 {safe_keyword}",
            f"🔄 Текущий статус: {status_label}",
            "",
            *_timing_lines(view),
            "",
            *_processing_state_lines(view),
            "",
            "Каскад решений (сжато):",
            *_cascade_lines(view.entry.steps, compact=True),
            "",
            *_summary_lines(view.entry),
        ]
        text = "\n".join(compact_lines)
        if len(text) <= MAX_MESSAGE_LENGTH:
            return text
        return _truncate_cascade_message(
            view=view,
            safe_nmid=safe_nmid,
            safe_keyword=safe_keyword,
            status_label=status_label,
        )

    return text[: MAX_MESSAGE_LENGTH - 20] + "\n…(обрезано)"


def _display_status_label(display_status: KeywordStatus) -> str:
    if display_status == KeywordStatus.GOOD:
        return "good"
    if display_status == KeywordStatus.BAD:
        return "bad"
    if display_status == KeywordStatus.VIEWS_IS_NOT_ENOUGH:
        return "pause"
    return display_status.value


def _format_tick_at_msk(tick_at: datetime | None) -> str:
    if tick_at is None:
        return "—"
    dt = tick_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_MSK_TZ).strftime(_TICK_TIME_FMT)


def _timing_lines(view: KeywordDecisionTraceViewData) -> list[str]:
    if view.tick_started_at is None and view.processing_started_at is None:
        return []
    return [
        f"Тик начат: {_format_tick_at_msk(view.tick_started_at)}",
        f"Обработка начата: {_format_tick_at_msk(view.processing_started_at)}",
        f"Тик завершён: {_format_tick_at_msk(view.tick_finished_at)}",
    ]


def _processing_state_lines(view: KeywordDecisionTraceViewData) -> list[str]:
    if view.trace_presence == TracePresence.ENTRY_FOUND:
        if view.processing_outcome == ProcessingOutcome.PROCESSED_UNCHANGED:
            return [
                "Ключ обрабатывался на последнем V3-тике, изменений не было.",
            ]
        return ["Ключ обрабатывался на последнем V3-тике."]
    if view.trace_presence == TracePresence.SNAPSHOT_NO_ENTRY:
        return [
            "Ключ не входил в V3 operable-обработку на последнем тике.",
        ]
    if view.source == "legacy_changes":
        return [
            "Нет полного trace: данные из legacy journal (не означает «обрабатывался»).",
        ]
    return [
        "Нет trace: неизвестно, обрабатывался ли ключ на последнем тике.",
    ]


def _step_time_label(step: KeywordDecisionTraceStep) -> str:
    if step.processed_at is not None:
        return _format_tick_at_msk(step.processed_at)
    return str(step.order)


def _cascade_lines(
    steps: list[KeywordDecisionTraceStep],
    *,
    compact: bool,
) -> list[str]:
    lines: list[str] = []
    for step in steps:
        short = short_label_for_executor(step.executor_name)
        title = title_ru_for_phase(phase_id_for_executor(step.executor_name))
        time_label = _step_time_label(step)
        if compact:
            lines.append(
                f"{step.order}. {short} · {step.status.value} · "
                f"{step.state_after}/{step.status_hint_after}"
            )
        else:
            lines.append(f"{step.order}. {title} ({short}) · {time_label}")
            lines.append(f"   {step.status.value}: {step.decision_ru}")
            lines.append(f"   state={step.state_after}, hint={step.status_hint_after}")
            if step.target_place_after is not None:
                lines.append(f"   tp={step.target_place_after}")
            lines.append(f"   {step.reason_ru}")
    return lines


def _summary_lines(entry: KeywordDecisionTraceEntry) -> list[str]:
    lines = [
        f"Итоговое решение: {entry.final_decision_ru}",
    ]
    if entry.decisive_executor:
        lines.append(f"Кто решил: {entry.decisive_executor}")
    if entry.decisive_reason_ru:
        lines.append(f"Почему: {entry.decisive_reason_ru}")
    elif not any(s.status in (TraceStepStatus.APPLY, TraceStepStatus.BLOCK) for s in entry.steps):
        lines.append(f"Почему: {REASON_NOT_IN_JOURNAL}")
    return lines


def _legacy_decisive_lines(
    decisive: V3KeywordStepRecord | str,
    tick_at: datetime | None,
) -> list[str]:
    parts = format_decisive_step_body(decisive)
    if parts is None:
        return ["нет записанного решения"]
    _short, title, body = parts
    lines = [f"{title}: {body}"]
    if isinstance(decisive, V3KeywordStepRecord):
        decision = DECISION_ACTION_LABEL.get(decisive.action, decisive.action)
        lines.append(f"Решение: {decision}")
        lines.append(f"Executor: {decisive.executor_name}")
    if tick_at is not None:
        lines.append(f"Время тика: {_format_tick_at_msk(tick_at)}")
    return lines


def _truncate_cascade_message(
    *,
    view: KeywordDecisionTraceViewData,
    safe_nmid: str,
    safe_keyword: str,
    status_label: str,
) -> str:
    """Head/tail truncate cascade с сохранением итога."""
    entry = view.entry
    assert entry is not None
    steps = entry.steps
    head = steps[:_TRUNCATE_HEAD]
    tail = steps[-_TRUNCATE_TAIL :] if len(steps) > _TRUNCATE_TAIL else []
    omitted = max(0, len(steps) - len(head) - len(tail))

    lines = [
        "🔎 *Почему бот так решил?*",
        "",
        f"📦 {safe_nmid}",
        f"🔑 {safe_keyword}",
        f"🔄 Текущий статус: {status_label}",
        "",
        *_timing_lines(view),
        "",
        *_processing_state_lines(view),
        "",
        "Каскад решений (сокращён):",
        *_cascade_lines(head, compact=True),
    ]
    if omitted > 0:
        lines.append(f"… ещё {omitted} шагов …")
    if tail and omitted > 0:
        lines.extend(_cascade_lines(tail, compact=True))
    lines.append("")
    lines.extend(_summary_lines(entry))
    text = "\n".join(lines)
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 24] + "\n…(обрезано по лимиту TG)"
    return text


def assert_no_forbidden_tokens(text: str) -> None:
    """Проверка отсутствия запрещённых токенов в UI (для тестов)."""
    upper = text.upper()
    for token in _FORBIDDEN_UI_TOKENS:
        if token.strip().upper() in upper:
            raise AssertionError(f"forbidden token {token!r} in text")


__all__ = [
    "format_keyword_decision_trace_screen",
    "keyword_v3_decision_trace_button_label",
    "assert_no_forbidden_tokens",
]
