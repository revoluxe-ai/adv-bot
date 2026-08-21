"""Coverage metadata для collect run (без дублирования raw payload)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CompletenessStatus(str, Enum):
    """Статус полноты family/endpoint."""

    FULL_AVAILABLE = "FULL_AVAILABLE"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class CoverageEntry:
    """Одна строка coverage report для endpoint/family."""

    family: str
    endpoint: str
    method: str
    http_statuses: list[int] = field(default_factory=list)
    api_calls: int = 0
    records_fetched: int = 0
    records_stored: int = 0
    min_date: str | None = None
    max_date: str | None = None
    min_last_change_date: str | None = None
    max_last_change_date: str | None = None
    unique_nmids: int | None = None
    unique_campaign_ids: int | None = None
    pagination_used: bool = False
    pagination_pages: int = 0
    window_count: int = 0
    rate_limit_retries: int = 0
    errors: list[str] = field(default_factory=list)
    completeness: CompletenessStatus = CompletenessStatus.PARTIAL
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Сериализация для report.json / manifest.json."""
        return {
            "family": self.family,
            "endpoint": self.endpoint,
            "method": self.method,
            "http_statuses": list(self.http_statuses),
            "api_calls": self.api_calls,
            "records_fetched": self.records_fetched,
            "records_stored": self.records_stored,
            "min_date": self.min_date,
            "max_date": self.max_date,
            "min_last_change_date": self.min_last_change_date,
            "max_last_change_date": self.max_last_change_date,
            "unique_nmids": self.unique_nmids,
            "unique_campaign_ids": self.unique_campaign_ids,
            "pagination_used": self.pagination_used,
            "pagination_pages": self.pagination_pages,
            "window_count": self.window_count,
            "rate_limit_retries": self.rate_limit_retries,
            "errors": list(self.errors),
            "completeness": self.completeness.value,
            "notes": list(self.notes),
        }

    def assert_integrity(self) -> None:
        """records_fetched must equal records_stored for successful raw datasets."""
        if self.records_fetched != self.records_stored:
            raise ArtifactIntegrityError(
                f"{self.family}/{self.endpoint}: fetched={self.records_fetched} "
                f"stored={self.records_stored}"
            )


class ArtifactIntegrityError(RuntimeError):
    """records_fetched != records_stored или иной artifact contract failure."""


def date_stats_from_rows(
    rows: list[dict[str, Any]],
    *,
    date_keys: tuple[str, ...] = ("date", "lastChangeDate"),
    last_change_keys: tuple[str, ...] = ("lastChangeDate", "last_change_date"),
    nmid_keys: tuple[str, ...] = ("nmId", "nm_id", "nmID"),
) -> dict[str, Any]:
    """Вычислить min/max dates и unique nmIDs по фактически сохранённым rows."""
    dates: list[str] = []
    last_changes: list[str] = []
    nmids: set[int] = set()
    for row in rows:
        for key in date_keys:
            val = row.get(key)
            if val and not str(val).startswith("0001"):
                dates.append(str(val)[:10])
        for key in last_change_keys:
            val = row.get(key)
            if val and not str(val).startswith("0001"):
                last_changes.append(str(val))
        for key in nmid_keys:
            val = row.get(key)
            if val is not None:
                try:
                    nmids.add(int(val))
                except (TypeError, ValueError):
                    pass
    return {
        "min_date": min(dates) if dates else None,
        "max_date": max(dates) if dates else None,
        "min_last_change_date": min(last_changes) if last_changes else None,
        "max_last_change_date": max(last_changes) if last_changes else None,
        "unique_nmids": len(nmids),
    }
