"""Поиск per-keyword entry и последнего решающего шага в post-hoc audit V3."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangeEntry,
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)


def find_keyword_change_entry(
    snapshot: V3KeywordChangesSnapshot | None,
    keyword_setting_id: int,
) -> V3KeywordChangeEntry | None:
    """Найти запись ключа в snapshot последнего V3-тика.

    Args:
        snapshot: Audit из Redis ``V3KeywordChanges:{adv_id}``; ``None`` — нет данных.
        keyword_setting_id: ID ``KeywordSetting``.

    Returns:
        Entry или ``None``, если ключ на тике не менялся.
    """
    if snapshot is None:
        return None
    for entry in snapshot.keyword_entries:
        if entry.keyword_setting_id == keyword_setting_id:
            return entry
    return None


def last_decisive_step(
    entry: V3KeywordChangeEntry,
) -> V3KeywordStepRecord | str | None:
    """Последний шаг, повлиявший на ключ на тике.

    Сначала — последний mode-step с ``action != "NOOP"`` (как в ``_build_keyword_entry``).
    Если mode-steps пусты или все NOOP — последний ``target_place_steps`` (tp-only).

    Args:
        entry: Per-keyword запись из ``build_keyword_changes_snapshot``.

    Returns:
        ``V3KeywordStepRecord`` для смены режима, строка ``"{place} ({short})"`` для tp-only
        или ``None``, если влияющих шагов нет.
    """
    for step in reversed(entry.steps):
        if step.action != "NOOP":
            return step
    if entry.target_place_steps:
        return entry.target_place_steps[-1]
    return None
