"""As-of границы event_date для history membership (UTC naive, как CH timeline)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.modules.attribution_facts.ports.campaign_settings_history import (
    HistorySnapshotView,
)


def event_date_observed_upper_bound(event_date: date) -> datetime:
    """Конец календарного event_date (exclusive верх для timeline query)."""
    next_day = event_date + timedelta(days=1)
    return datetime.combine(next_day, time.min)


def event_date_observed_lower_bound(event_date: date) -> datetime:
    """Начало календарного event_date для timeline query."""
    return datetime.combine(event_date, time.min)


def select_as_of_snapshot(
    snapshots: tuple[HistorySnapshotView, ...],
    event_date: date,
) -> HistorySnapshotView | None:
    """
    Выбрать latest snapshot с observed_at <= конец event_date.

    Args:
        snapshots: Уже отфильтрованный timeline.
        event_date: Календарный день факта.
    """
    upper = event_date_observed_upper_bound(event_date)
    eligible = [s for s in snapshots if s.observed_at < upper]
    if not eligible:
        return None
    return max(eligible, key=lambda s: (s.observed_at, s.snapshot_id))
