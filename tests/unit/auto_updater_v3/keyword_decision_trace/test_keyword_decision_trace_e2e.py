"""E2E-style unit: collector → snapshot → Redis roundtrip → ViewData → formatter."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.client_bot.user_interface.services.keyword_decision_trace_loader import (
    KeywordDecisionTraceViewData,
    ProcessingOutcome,
    TracePresence,
)
from app.client_bot.user_interface.views.keyword_decision_trace_ui import (
    assert_no_forbidden_tokens,
    format_keyword_decision_trace_screen,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.builder import (
    build_keyword_decision_trace_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.collector import (
    KeywordDecisionTraceCollector,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceSnapshot,
    TraceStepStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.query import (
    find_trace_entry,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.hard_status_validate import (
    HardStatusValidateExecutor,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from tests.unit.auto_updater_v3.keyword_decision_trace.test_keyword_decision_trace_collector import (
    _dto,
    _minimal_context,
)


def _redis_json_roundtrip(snapshot: KeywordDecisionTraceSnapshot) -> KeywordDecisionTraceSnapshot:
    """Тот же JSON-путь, что ``KeywordDecisionTraceRedisCache.set/get``."""
    data = json.loads(snapshot.model_dump_json())
    return KeywordDecisionTraceSnapshot.model_validate(data)


@pytest.mark.unit
def test_keyword_decision_trace_e2e_unchanged_off_through_redis_to_formatter() -> None:
    """Связка collector → snapshot → cache JSON → ViewData → formatter text."""
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    ks_id = 99
    keyword_text = "off bad keyword"

    collector = KeywordDecisionTraceCollector()
    collector.start_tick(tick_started_at=tick)
    off_dto = _dto(ks_id, mode=KeywordStrategyMode.OFF)
    off_dto.calculated_keyword.keyword_setting.text = keyword_text
    collector.register_operable_keywords([off_dto])

    ctx = _minimal_context([off_dto])
    executor = HardStatusValidateExecutor()
    executor.execute(ctx)
    collector.record_executor_phase(
        context=ctx,
        executor=executor,
        order=1,
        steps_before={ks_id: 0},
        tp_steps_before={ks_id: 0},
        skip_reason=executor.skip_reason,
    )

    snapshot = build_keyword_decision_trace_snapshot(
        collector,
        adv_id=519358830,
        tick_finished_at=tick,
        nmids=[519358830],
    )
    assert snapshot.operable_keywords == 1
    assert len(snapshot.entries) == 1

    built_entry = snapshot.entries[0]
    assert built_entry.processing_started is True
    assert built_entry.net_changed is False
    assert built_entry.steps
    assert built_entry.steps[0].status in (TraceStepStatus.SKIP, TraceStepStatus.PASS)

    loaded = _redis_json_roundtrip(snapshot)
    entry = find_trace_entry(loaded, keyword_setting_id=ks_id)
    assert entry is not None
    assert entry.processing_started is True
    assert entry.net_changed is False
    assert entry.steps
    assert entry.steps[0].status in (TraceStepStatus.SKIP, TraceStepStatus.PASS)

    view = KeywordDecisionTraceViewData(
        nmid_display="519358830",
        keyword_text=keyword_text,
        display_status=KeywordStatus.BAD,
        bot_active=True,
        keyword_setting_id=ks_id,
        trace_presence=TracePresence.ENTRY_FOUND,
        processing_outcome=ProcessingOutcome.PROCESSED_UNCHANGED,
        tick_started_at=loaded.tick_started_at,
        processing_started_at=loaded.processing_started_at,
        tick_finished_at=loaded.tick_finished_at,
        entry=entry,
        source="trace",
    )

    text = format_keyword_decision_trace_screen(view)
    assert "обрабатывался" in text
    assert "изменений не было" in text
    assert entry.steps[0].executor_name == "HardStatusValidateExecutor"
    assert "validate hard_status" in text or " · V · " in text
    assert "Каскад решений" in text
    assert "SKIP" in text or "PASS" in text
    assert_no_forbidden_tokens(text)
