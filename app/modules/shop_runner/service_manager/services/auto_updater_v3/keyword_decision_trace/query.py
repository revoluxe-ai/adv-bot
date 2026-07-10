"""Lookup helpers для KeywordDecisionTraceSnapshot."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceSnapshot,
)


def find_trace_entry(
    snapshot: KeywordDecisionTraceSnapshot | None,
    *,
    keyword_setting_id: int | None = None,
    keyword_text: str | None = None,
    nmid: int | None = None,
) -> KeywordDecisionTraceEntry | None:
    """Найти entry в snapshot по id, тексту или nmid+текст.

    Args:
        snapshot: Загруженный trace; ``None`` → ``None``.
        keyword_setting_id: Primary key (``KeywordSetting.id``).
        keyword_text: Case-insensitive match.
        nmid: Опциональный фильтр по артикулу кампании.

    Returns:
        Entry или ``None``.
    """
    if snapshot is None:
        return None
    if keyword_setting_id is not None:
        entry = snapshot.find_by_keyword_setting_id(keyword_setting_id)
        if entry is None:
            return None
        if nmid is not None and nmid not in entry.nmids:
            return None
        return entry
    if keyword_text is not None:
        entry = snapshot.find_by_keyword_text(keyword_text)
        if entry is None:
            return None
        if nmid is not None and nmid not in entry.nmids:
            return None
        return entry
    return None
