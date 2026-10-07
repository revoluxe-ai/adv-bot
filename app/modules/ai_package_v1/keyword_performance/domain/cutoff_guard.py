"""Post-fetch cutoff guards when source rows bypass SQL filters.

Defense-in-depth: SQL readers bind cutoff parameters, but export assembly MUST
exclude out-of-contract rows and derive bounds from valid observations only.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader import (
    RawBidDecisionRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader import (
    RawDailySnapshotRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    RawPositionRow,
)


def _as_utc_instant(value: datetime) -> datetime:
    """Normalize naive or aware datetime to UTC for cutoff comparison."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def daily_snapshot_within_cutoff(
    stat_date: date,
    last_snapshot_ts: datetime | None,
    cutoff: PackageCutoff,
) -> bool:
    """True when daily fact respects date and same-day instant cutoff."""
    if stat_date > cutoff.package_cutoff_date:
        return False
    if (
        stat_date == cutoff.package_cutoff_date
        and last_snapshot_ts is not None
        and _as_utc_instant(last_snapshot_ts) > cutoff.package_cutoff_instant
    ):
        return False
    return True


def position_snapshot_within_cutoff(
    stat_date: date,
    version: int | None,
    cutoff: PackageCutoff,
) -> bool:
    """True when position row respects date and proven version-ms cutoff."""
    if stat_date > cutoff.package_cutoff_date:
        return False
    if version is not None and version > cutoff.cutoff_instant_ms:
        return False
    return True


def bid_decision_within_cutoff(
    decision_time: datetime | None,
    stats_max_timestamp: datetime | None,
    cutoff: PackageCutoff,
) -> bool:
    """True when decision row respects package_cutoff_instant on all timestamps."""
    if (
        decision_time is not None
        and _as_utc_instant(decision_time) > cutoff.package_cutoff_instant
    ):
        return False
    if (
        stats_max_timestamp is not None
        and _as_utc_instant(stats_max_timestamp) > cutoff.package_cutoff_instant
    ):
        return False
    return True


def filter_daily_rows(
    rows: list[RawDailySnapshotRow],
    cutoff: PackageCutoff,
) -> list[RawDailySnapshotRow]:
    """Drop daily rows outside package cutoff (date + same-day instant)."""
    return [
        row
        for row in rows
        if daily_snapshot_within_cutoff(
            row.stat_date, row.last_snapshot_ts, cutoff
        )
    ]


def filter_position_rows(
    rows: list[RawPositionRow],
    cutoff: PackageCutoff,
) -> list[RawPositionRow]:
    """Drop position rows outside package cutoff (date + version ms)."""
    return [
        row
        for row in rows
        if position_snapshot_within_cutoff(row.stat_date, row.version, cutoff)
    ]


def filter_bid_decision_rows(
    rows: list[RawBidDecisionRow],
    cutoff: PackageCutoff,
) -> list[RawBidDecisionRow]:
    """Drop decision rows with timestamps after package_cutoff_instant."""
    return [
        row
        for row in rows
        if bid_decision_within_cutoff(
            row.decision_time, row.stats_max_timestamp, cutoff
        )
    ]


def effective_last_available(
    *,
    ch_last: date | None,
    observed_dates: tuple[date, ...],
    cutoff: PackageCutoff,
) -> date | None:
    """Derive last_available from valid observations; never report future CH dates.

    When valid rows exist, ``max(observed)`` wins. When CH bound is future-only
    with no in-cutoff observations, returns ``None`` (no synthetic cutoff fill).
    """
    valid = [d for d in observed_dates if d <= cutoff.package_cutoff_date]
    if valid:
        return max(valid)
    if ch_last is None or ch_last > cutoff.package_cutoff_date:
        return None
    return ch_last
