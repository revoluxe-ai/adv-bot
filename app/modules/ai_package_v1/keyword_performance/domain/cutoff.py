"""Package cutoff semantics: UTC instant + date from manifest generated_at."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


@dataclass(frozen=True, slots=True)
class PackageCutoff:
    """Stable cutoff instant shared across all keyword source filters."""

    package_cutoff_instant: datetime
    package_cutoff_date: date
    cutoff_instant_ms: int
    last_closed_calendar_day: date

    @classmethod
    def from_generated_at(cls, generated_at: str) -> PackageCutoff:
        """Parse ISO-8601 UTC ``generated_at`` into cutoff fields.

        Args:
            generated_at: Manifest timestamp (e.g. ``2026-10-03T12:00:00Z``).

        Returns:
            ``PackageCutoff`` with UTC date and epoch-ms for CH version filter.
        """
        instant = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        else:
            instant = instant.astimezone(UTC)
        cutoff_date = instant.date()
        cutoff_ms = int(instant.timestamp() * 1000)
        last_closed = cutoff_date - timedelta(days=1)
        return cls(
            package_cutoff_instant=instant,
            package_cutoff_date=cutoff_date,
            cutoff_instant_ms=cutoff_ms,
            last_closed_calendar_day=last_closed,
        )
