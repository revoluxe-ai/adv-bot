"""Загрузка ViewData для экрана «Почему бот так решил?» (PG + Redis, без форматирования)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.query import (
    find_trace_entry,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.redis import (
    KeywordDecisionTraceRedisCache,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.keyword_entry import (
    find_keyword_change_entry,
    last_decisive_step,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.redis import (
    V3KeywordChangesRedisCache,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.utils.db.session_maker import get_async_session_maker as sm


class TracePresence(StrEnum):
    """Наличие trace entry для ключа в последнем snapshot."""

    ENTRY_FOUND = "entry_found"
    SNAPSHOT_NO_ENTRY = "snapshot_no_entry"
    NO_SNAPSHOT = "no_snapshot"


class ProcessingOutcome(StrEnum):
    """Исход обработки ключа на последнем V3-тике."""

    PROCESSED_CHANGED = "processed_changed"
    PROCESSED_UNCHANGED = "processed_unchanged"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class KeywordDecisionTraceViewData:
    """DTO для pure formatter (без I/O)."""

    nmid_display: str
    keyword_text: str
    display_status: KeywordStatus
    bot_active: bool
    keyword_setting_id: int

    trace_presence: TracePresence
    processing_outcome: ProcessingOutcome

    tick_started_at: datetime | None
    processing_started_at: datetime | None
    tick_finished_at: datetime | None

    entry: KeywordDecisionTraceEntry | None
    source: Literal["trace", "legacy_changes", "empty", "non_v3"]
    legacy_decisive: V3KeywordStepRecord | str | None = None
    legacy_tick_at: datetime | None = None


def _display_status_from_db_and_cache(
    keyword_setting: KeywordSetting,
    calculated_keyword: CalculatedKeyword | None,
) -> KeywordStatus:
    """Текущий статус для UI: из БД для 0/3/4, иначе из кеша."""
    hard = keyword_setting.hard_status
    if hard == 4:
        return KeywordStatus.GOOD
    if hard == 3:
        return KeywordStatus.BAD
    if hard == 0:
        return KeywordStatus.BAD
    if calculated_keyword is not None:
        return calculated_keyword.status
    return KeywordStatus.BAD


async def load_keyword_decision_trace_view(
    *,
    keyword_setting_id: int,
) -> KeywordDecisionTraceViewData:
    """Загрузить данные экрана trace: PG + Redis (+ legacy fallback).

    Args:
        keyword_setting_id: ``KeywordSetting.id``.

    Returns:
        ViewData для ``format_keyword_decision_trace_screen``.
    """
    async with sm(read_only=True) as session:
        stmt = (
            select(KeywordSetting)
            .options(selectinload(KeywordSetting.adv_setting))
            .where(KeywordSetting.id == keyword_setting_id)
        )
        result = await session.execute(stmt)
        keyword_setting = result.scalar_one_or_none()

    if keyword_setting is None:
        return KeywordDecisionTraceViewData(
            nmid_display="—",
            keyword_text="",
            display_status=KeywordStatus.BAD,
            bot_active=False,
            keyword_setting_id=keyword_setting_id,
            trace_presence=TracePresence.NO_SNAPSHOT,
            processing_outcome=ProcessingOutcome.UNKNOWN,
            tick_started_at=None,
            processing_started_at=None,
            tick_finished_at=None,
            entry=None,
            source="empty",
        )

    adv_setting: AdvSetting = keyword_setting.adv_setting
    nmids = [str(n) for n in list(adv_setting.nmids or [])]
    nmid_display = ", ".join(nmids) if nmids else "—"

    cache = RedisCalculatedKeywordsCacheManager()
    calculated_keyword = await cache.get_calculated_keyword(
        adv_setting.adv_id,
        keyword_setting.text,
    )
    display_status = _display_status_from_db_and_cache(
        keyword_setting,
        calculated_keyword,
    )

    if not adv_setting.bot_active:
        return KeywordDecisionTraceViewData(
            nmid_display=nmid_display,
            keyword_text=keyword_setting.text,
            display_status=display_status,
            bot_active=False,
            keyword_setting_id=keyword_setting_id,
            trace_presence=TracePresence.NO_SNAPSHOT,
            processing_outcome=ProcessingOutcome.UNKNOWN,
            tick_started_at=None,
            processing_started_at=None,
            tick_finished_at=None,
            entry=None,
            source="non_v3",
        )

    trace_snapshot: KeywordDecisionTraceSnapshot | None = (
        await KeywordDecisionTraceRedisCache(adv_setting).get()
    )
    entry = find_trace_entry(trace_snapshot, keyword_setting_id=keyword_setting_id)

    if trace_snapshot is not None and entry is not None:
        outcome = (
            ProcessingOutcome.PROCESSED_CHANGED
            if entry.net_changed
            else ProcessingOutcome.PROCESSED_UNCHANGED
        )
        return KeywordDecisionTraceViewData(
            nmid_display=nmid_display,
            keyword_text=keyword_setting.text,
            display_status=display_status,
            bot_active=True,
            keyword_setting_id=keyword_setting_id,
            trace_presence=TracePresence.ENTRY_FOUND,
            processing_outcome=outcome,
            tick_started_at=trace_snapshot.tick_started_at,
            processing_started_at=trace_snapshot.processing_started_at,
            tick_finished_at=trace_snapshot.tick_finished_at,
            entry=entry,
            source="trace",
        )

    if trace_snapshot is not None and entry is None:
        return KeywordDecisionTraceViewData(
            nmid_display=nmid_display,
            keyword_text=keyword_setting.text,
            display_status=display_status,
            bot_active=True,
            keyword_setting_id=keyword_setting_id,
            trace_presence=TracePresence.SNAPSHOT_NO_ENTRY,
            processing_outcome=ProcessingOutcome.UNKNOWN,
            tick_started_at=trace_snapshot.tick_started_at,
            processing_started_at=trace_snapshot.processing_started_at,
            tick_finished_at=trace_snapshot.tick_finished_at,
            entry=None,
            source="trace",
        )

    # TODO: убрать fallback на V3KeywordChangesSnapshot после полного
    # перехода на KeywordDecisionTraceSnapshot (все prod ticks пишут trace).
    legacy: V3KeywordChangesSnapshot | None = (
        await V3KeywordChangesRedisCache(adv_setting).get()
    )
    legacy_entry = (
        find_keyword_change_entry(legacy, keyword_setting_id)
        if legacy is not None
        else None
    )
    legacy_decisive = (
        last_decisive_step(legacy_entry) if legacy_entry is not None else None
    )
    if legacy is not None and legacy_decisive is not None:
        return KeywordDecisionTraceViewData(
            nmid_display=nmid_display,
            keyword_text=keyword_setting.text,
            display_status=display_status,
            bot_active=True,
            keyword_setting_id=keyword_setting_id,
            trace_presence=TracePresence.NO_SNAPSHOT,
            processing_outcome=ProcessingOutcome.UNKNOWN,
            tick_started_at=None,
            processing_started_at=None,
            tick_finished_at=None,
            entry=None,
            source="legacy_changes",
            legacy_decisive=legacy_decisive,
            legacy_tick_at=legacy.tick_at,
        )

    return KeywordDecisionTraceViewData(
        nmid_display=nmid_display,
        keyword_text=keyword_setting.text,
        display_status=display_status,
        bot_active=True,
        keyword_setting_id=keyword_setting_id,
        trace_presence=TracePresence.NO_SNAPSHOT,
        processing_outcome=ProcessingOutcome.UNKNOWN,
        tick_started_at=None,
        processing_started_at=None,
        tick_finished_at=None,
        entry=None,
        source="empty",
    )
