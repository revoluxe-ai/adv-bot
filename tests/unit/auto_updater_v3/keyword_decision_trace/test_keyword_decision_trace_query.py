"""Unit: find_trace_entry helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.query import (
    find_trace_entry,
)


def _entry(ks_id: int, text: str) -> KeywordDecisionTraceEntry:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    return KeywordDecisionTraceEntry(
        keyword_setting_id=ks_id,
        keyword_text=text,
        nmids=[111, 222],
        nmid_display="111, 222",
        processing_started_at=tick,
        status_hint_before="off-like",
        state_before="OFF",
        status_hint_after="off-like",
        state_after="OFF",
        final_decision_ru="Без изменений",
        steps=[],
    )


@pytest.mark.unit
def test_find_by_keyword_setting_id() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    snap = KeywordDecisionTraceSnapshot(
        tick_started_at=tick,
        processing_started_at=tick,
        tick_at=tick,
        adv_id=1,
        operable_keywords=1,
        entries=[_entry(42, "alpha")],
    )
    assert find_trace_entry(snap, keyword_setting_id=42) is not None
    assert find_trace_entry(snap, keyword_setting_id=99) is None


@pytest.mark.unit
def test_find_by_keyword_text_case_insensitive() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    snap = KeywordDecisionTraceSnapshot(
        tick_started_at=tick,
        processing_started_at=tick,
        tick_at=tick,
        adv_id=1,
        operable_keywords=1,
        entries=[_entry(1, "Alpha Beta")],
    )
    assert find_trace_entry(snap, keyword_text="alpha beta") is not None


@pytest.mark.unit
def test_find_with_nmid_filter() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    snap = KeywordDecisionTraceSnapshot(
        tick_started_at=tick,
        processing_started_at=tick,
        tick_at=tick,
        adv_id=1,
        operable_keywords=1,
        entries=[_entry(1, "kw")],
    )
    assert find_trace_entry(snap, keyword_setting_id=1, nmid=111) is not None
    assert find_trace_entry(snap, keyword_setting_id=1, nmid=999) is None
