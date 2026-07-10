"""Unit: KeywordDecisionTraceSnapshot JSON roundtrip."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceSnapshot,
    KeywordDecisionTraceStep,
    TraceStepStatus,
)


def _sample_snapshot() -> KeywordDecisionTraceSnapshot:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    step = KeywordDecisionTraceStep(
        order=1,
        phase_id="validate_state_by_hard_status",
        executor_name="HardStatusValidateExecutor",
        status=TraceStepStatus.SKIP,
        decision_ru="не менять",
        reason_ru="Причина не зафиксирована в executor'е",
        state_after="OFF",
        status_hint_after="off-like",
        processed_at=tick,
    )
    entry = KeywordDecisionTraceEntry(
        keyword_setting_id=42,
        keyword_text="kw",
        nmids=[111],
        nmid_display="111",
        processing_started_at=tick,
        status_hint_before="off-like",
        state_before="OFF",
        status_hint_after="off-like",
        state_after="OFF",
        final_decision_ru="Без изменений (ключ обрабатывался)",
        steps=[step],
        net_changed=False,
    )
    return KeywordDecisionTraceSnapshot(
        tick_started_at=tick,
        processing_started_at=tick,
        tick_finished_at=tick,
        tick_at=tick,
        adv_id=99,
        operable_keywords=1,
        nmids=[111],
        entries=[entry],
    )


@pytest.mark.unit
def test_snapshot_json_roundtrip() -> None:
    original = _sample_snapshot()
    data = json.loads(original.model_dump_json())
    loaded = KeywordDecisionTraceSnapshot.model_validate(data)
    assert loaded.adv_id == 99
    assert loaded.entries[0].keyword_setting_id == 42
    assert loaded.entries[0].steps[0].status == TraceStepStatus.SKIP
