"""Unit: format_keyword_decision_trace_screen (cascade, Telegram limits)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.client_bot.const import MAX_MESSAGE_LENGTH
from app.client_bot.user_interface.services.keyword_decision_trace_loader import (
    KeywordDecisionTraceViewData,
    ProcessingOutcome,
    TracePresence,
)
from app.client_bot.user_interface.views.keyword_decision_trace_ui import (
    assert_no_forbidden_tokens,
    format_keyword_decision_trace_screen,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceStep,
    TraceStepStatus,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)


def _step(order: int, *, phase: str = "validate_state_by_hard_status") -> KeywordDecisionTraceStep:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    return KeywordDecisionTraceStep(
        order=order,
        phase_id=phase,
        executor_name="HardStatusValidateExecutor",
        status=TraceStepStatus.SKIP,
        decision_ru="не менять",
        reason_ru="Причина не зафиксирована в executor'е",
        state_after="OFF",
        status_hint_after="off-like",
        target_place_after=0,
        processed_at=tick,
    )


def _entry(steps: list[KeywordDecisionTraceStep]) -> KeywordDecisionTraceEntry:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    return KeywordDecisionTraceEntry(
        keyword_setting_id=42,
        keyword_text="test keyword",
        nmids=[519358830],
        nmid_display="519358830",
        processing_started_at=tick,
        status_hint_before="off-like",
        state_before="OFF",
        status_hint_after="off-like",
        state_after="OFF",
        final_decision_ru="Без изменений (ключ обрабатывался)",
        steps=steps,
        net_changed=False,
    )


def _view(
    *,
    entry: KeywordDecisionTraceEntry | None = None,
    presence: TracePresence = TracePresence.ENTRY_FOUND,
    outcome: ProcessingOutcome = ProcessingOutcome.PROCESSED_UNCHANGED,
) -> KeywordDecisionTraceViewData:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    return KeywordDecisionTraceViewData(
        nmid_display="519358830",
        keyword_text="test keyword",
        display_status=KeywordStatus.BAD,
        bot_active=True,
        keyword_setting_id=42,
        trace_presence=presence,
        processing_outcome=outcome,
        tick_started_at=tick,
        processing_started_at=tick,
        tick_finished_at=tick,
        entry=entry,
        source="trace",
    )


@pytest.mark.unit
def test_formatter_processed_unchanged_message() -> None:
    entry = _entry([_step(1)])
    text = format_keyword_decision_trace_screen(_view(entry=entry))
    assert "обрабатывался" in text
    assert "изменений не было" in text
    assert "Каскад решений" in text
    assert_no_forbidden_tokens(text)


@pytest.mark.unit
def test_formatter_no_trace_message() -> None:
    text = format_keyword_decision_trace_screen(
        KeywordDecisionTraceViewData(
            nmid_display="1",
            keyword_text="kw",
            display_status=KeywordStatus.BAD,
            bot_active=True,
            keyword_setting_id=1,
            trace_presence=TracePresence.NO_SNAPSHOT,
            processing_outcome=ProcessingOutcome.UNKNOWN,
            tick_started_at=None,
            processing_started_at=None,
            tick_finished_at=None,
            entry=None,
            source="empty",
        )
    )
    assert "неизвестно" in text
    assert "Каскад решений" not in text


@pytest.mark.unit
def test_formatter_message_length_within_telegram_limit() -> None:
    steps = [_step(i) for i in range(1, 17)]
    entry = _entry(steps)
    text = format_keyword_decision_trace_screen(_view(entry=entry))
    assert len(text) <= MAX_MESSAGE_LENGTH


@pytest.mark.unit
def test_formatter_compact_truncate_fallback() -> None:
    steps = [_step(i) for i in range(1, 25)]
    entry = _entry(steps)
    # длинные reason_ru чтобы превысить лимит даже в compact
    long_steps = [
        step.model_copy(
            update={
                "reason_ru": "x" * 200,
                "decision_ru": "y" * 80,
            }
        )
        for step in steps
    ]
    entry = entry.model_copy(update={"steps": long_steps})
    text = format_keyword_decision_trace_screen(_view(entry=entry))
    assert len(text) <= MAX_MESSAGE_LENGTH
    assert "Итоговое решение" in text
    assert "ещё" in text or "сокращён" in text or "сжато" in text
