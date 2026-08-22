"""Unit: load_keyword_decision_trace_view fallback chain."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.services.keyword_decision_trace_loader import (
    ProcessingOutcome,
    TracePresence,
    load_keyword_decision_trace_view,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangeEntry,
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)


def _keyword_setting() -> MagicMock:
    ks = MagicMock()
    ks.id = 42
    ks.text = "test kw"
    ks.hard_status = 1
    adv = MagicMock()
    adv.adv_id = 99
    adv.bot_active = True
    adv.nmids = [519358830]
    ks.adv_setting = adv
    return ks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_loader_primary_trace() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    entry = KeywordDecisionTraceEntry(
        keyword_setting_id=42,
        keyword_text="test kw",
        processing_started_at=tick,
        status_hint_before="off-like",
        state_before="OFF",
        status_hint_after="off-like",
        state_after="OFF",
        final_decision_ru="Без изменений",
        net_changed=False,
    )
    trace = KeywordDecisionTraceSnapshot(
        tick_started_at=tick,
        processing_started_at=tick,
        tick_finished_at=tick,
        tick_at=tick,
        adv_id=99,
        operable_keywords=1,
        entries=[entry],
    )
    ks = _keyword_setting()
    with (
        patch(
            "app.client_bot.user_interface.services.keyword_decision_trace_loader.sm"
        ) as sm_mock,
        patch(
            "app.client_bot.user_interface.services.keyword_decision_trace_loader.RedisCalculatedKeywordsCacheManager"
        ) as calc_cls,
        patch(
            "app.client_bot.user_interface.services.keyword_decision_trace_loader.KeywordDecisionTraceRedisCache"
        ) as trace_cls,
    ):
        session = AsyncMock()
        sm_mock.return_value.__aenter__.return_value = session
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=ks))
        )
        calc = calc_cls.return_value
        calc.get_calculated_keyword = AsyncMock(return_value=None)
        trace_cache = trace_cls.return_value
        trace_cache.get = AsyncMock(return_value=trace)

        view = await load_keyword_decision_trace_view(keyword_setting_id=42)

    assert view.trace_presence == TracePresence.ENTRY_FOUND
    assert view.processing_outcome == ProcessingOutcome.PROCESSED_UNCHANGED
    assert view.source == "trace"
    assert view.tick_started_at == tick


@pytest.mark.unit
@pytest.mark.asyncio
async def test_loader_fallback_legacy_only_when_no_snapshot() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    legacy = V3KeywordChangesSnapshot(
        tick_at=tick,
        adv_id=99,
        keyword_entries=[
            V3KeywordChangeEntry(
                keyword_setting_id=42,
                keyword_text="test kw",
                stored_mode="OFF",
                current_mode="MIN_CPA",
                steps=[
                    V3KeywordStepRecord(
                        executor_name="RaiseStateToTargetCpoExecutor",
                        from_mode="OFF",
                        to_mode="MIN_CPA",
                        action="UP",
                    ),
                ],
            ),
        ],
    )
    ks = _keyword_setting()
    with (
        patch(
            "app.client_bot.user_interface.services.keyword_decision_trace_loader.sm"
        ) as sm_mock,
        patch(
            "app.client_bot.user_interface.services.keyword_decision_trace_loader.RedisCalculatedKeywordsCacheManager"
        ) as calc_cls,
        patch(
            "app.client_bot.user_interface.services.keyword_decision_trace_loader.KeywordDecisionTraceRedisCache"
        ) as trace_cls,
        patch(
            "app.client_bot.user_interface.services.keyword_decision_trace_loader.V3KeywordChangesRedisCache"
        ) as legacy_cls,
    ):
        session = AsyncMock()
        sm_mock.return_value.__aenter__.return_value = session
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=ks))
        )
        calc_cls.return_value.get_calculated_keyword = AsyncMock(return_value=None)
        trace_cls.return_value.get = AsyncMock(return_value=None)
        legacy_cls.return_value.get = AsyncMock(return_value=legacy)

        view = await load_keyword_decision_trace_view(keyword_setting_id=42)

    assert view.source == "legacy_changes"
    assert view.trace_presence == TracePresence.NO_SNAPSHOT
    assert view.legacy_decisive is not None
