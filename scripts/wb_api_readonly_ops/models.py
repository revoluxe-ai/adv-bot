"""DTO и статусы для WB read-only preflight/collect отчёта."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Mode(str, Enum):
    """Режим запуска entrypoint."""

    PREFLIGHT = "preflight"
    COLLECT = "collect"


class ArtifactClass(str, Enum):
    """Класс артефакта: contract RETURN primary vs L0 side vs clean_dump.

    Spec: Explicit contract and artifact-class CLI surface;
    decision wb-readonly-contract-return-vs-l0.
    """

    CONTRACT_PREFLIGHT = "contract_preflight"
    L0_RESEARCH = "l0_research"
    CLEAN_DUMP = "clean_dump"


class FamilyName(str, Enum):
    """Семьи endpoint aliases (INC-RO-01 + INC-RO-06 ORDERS)."""

    ORDERS_OR_SALES_REPORTS_READ = "orders_or_sales_reports_read"
    ADS = "ads"
    CARDS = "cards"
    ANALYTICS = "analytics"
    NORMS = "norms"


# COL-R03 pilot Stage A: dateFrom start (Europe/Moscow calendar date).
ORDERS_PERIOD_DATE_FROM_DEFAULT: dt.date = dt.date(2026, 7, 4)


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
    FamilyName.ORDERS_OR_SALES_REPORTS_READ,
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
    """Структурированный отчёт Owner-local / contract run (не Web PASS claim)."""

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
    artifact_class: str | None = None
    contract_id: str | None = None
    primary_artifact: str | None = None
    primary_sha256: str | None = None
    l0_side_artifact: str | None = None
    web_collector_handoff: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Сериализация отчёта; web_pass_claimed всегда false для этого класса.

        Spec: Operator report exposes contract artifact fields
        (ARTIFACT_CLASS / PRIMARY_* / L0_SIDE / WEB_COLLECTOR_HANDOFF /
        CONTRACT_ID); зеркала SIDE_ARTIFACT / EXTERNAL_HANDOFF_READY.
        """
        handoff = bool(
            self.web_collector_handoff
            and self.primary_artifact
            and self.primary_sha256
        )
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
            "ARTIFACT_CLASS": self.artifact_class,
            "PRIMARY_ARTIFACT": self.primary_artifact,
            "PRIMARY_SHA256": self.primary_sha256,
            "L0_SIDE_ARTIFACT": self.l0_side_artifact or "NONE",
            "SIDE_ARTIFACT": self.l0_side_artifact or "NONE",
            "WEB_COLLECTOR_HANDOFF": "YES" if handoff else "NO",
            "EXTERNAL_HANDOFF_READY": "YES" if handoff else "NO",
            "CONTRACT_ID": self.contract_id or "NONE",
            "note": (
                "Owner-local research dump (secret-strip) and/or contract "
                "RETURN. NOT Web READ_ONLY_PREFLIGHT_PASS / CLEAN_DUMP."
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
