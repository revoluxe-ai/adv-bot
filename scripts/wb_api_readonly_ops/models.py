"""DTO и статусы для WB read-only preflight/collect отчёта."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Mode(str, Enum):
    """Режим запуска entrypoint."""

    PREFLIGHT = "preflight"
    COLLECT = "collect"


class FamilyName(str, Enum):
    """Четыре семьи endpoint aliases (INC-RO-01)."""

    ADS = "ads"
    CARDS = "cards"
    ANALYTICS = "analytics"
    NORMS = "norms"


class FamilyStatus(str, Enum):
    """Статус одной семьи данных."""

    OK = "OK"
    PARTIAL = "PARTIAL"
    GAP = "GAP"
    FAILED = "FAILED"


class OverallStatus(str, Enum):
    """Итоговый статус прогона (не Web PASS)."""

    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


FAMILY_ORDER: tuple[FamilyName, ...] = (
    FamilyName.ADS,
    FamilyName.CARDS,
    FamilyName.ANALYTICS,
    FamilyName.NORMS,
)


def _empty_str_list() -> list[str]:
    """Typed default_factory для list[str]."""
    return []


@dataclass
class FamilyResult:
    """Результат probe/collect по одной семье."""

    family: FamilyName
    status: FamilyStatus
    gaps: list[str] = field(default_factory=_empty_str_list)
    error: str | None = None
    payload: Any = None
    notes: list[str] = field(default_factory=_empty_str_list)

    def to_dict(self) -> dict[str, Any]:
        """Сериализация семьи для report JSON."""
        return {
            "family": self.family.value,
            "status": self.status.value,
            "gaps": list(self.gaps),
            "error": self.error,
            "notes": list(self.notes),
            "payload": self.payload,
        }


@dataclass
class RunReport:
    """Структурированный отчёт Owner-local research dump (не Web CLEAN_DUMP)."""

    mode: Mode
    shop_id: str
    overall_status: OverallStatus
    families: list[FamilyResult]
    ceiling_max_seconds: float
    ceiling_max_calls: int
    ceiling_calls_used: int
    ceiling_exhausted: bool
    archive_sha256: str | None = None
    label: str = "owner_local_research_dump"
    web_pass_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Сериализация отчёта; web_pass_claimed всегда false для этого класса."""
        return {
            "label": self.label,
            "mode": self.mode.value,
            "shop_id": self.shop_id,
            "overall_status": self.overall_status.value,
            "families": [f.to_dict() for f in self.families],
            "ceiling": {
                "max_seconds": self.ceiling_max_seconds,
                "max_calls": self.ceiling_max_calls,
                "calls_used": self.ceiling_calls_used,
                "exhausted": self.ceiling_exhausted,
            },
            "archive_sha256": self.archive_sha256,
            "web_pass_claimed": False,
            "note": (
                "Owner-local research dump (secret-strip). "
                "NOT Web READ_ONLY_PREFLIGHT_PASS / CLEAN_DUMP."
            ),
        }


def compute_overall_status(families: list[FamilyResult]) -> OverallStatus:
    """Итог: OK только если все семьи OK и без gaps; иначе PARTIAL/FAILED."""
    if not families:
        return OverallStatus.FAILED
    if any(f.status == FamilyStatus.FAILED for f in families) and all(
        f.status in (FamilyStatus.FAILED, FamilyStatus.GAP) for f in families
    ):
        return OverallStatus.FAILED
    has_gap = any(
        f.gaps
        or f.status
        in (FamilyStatus.PARTIAL, FamilyStatus.GAP, FamilyStatus.FAILED)
        for f in families
    )
    if has_gap:
        return OverallStatus.PARTIAL
    if all(f.status == FamilyStatus.OK for f in families):
        return OverallStatus.OK
    return OverallStatus.PARTIAL
