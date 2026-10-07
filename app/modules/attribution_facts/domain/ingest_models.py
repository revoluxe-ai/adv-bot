"""Модели ingest Slice B (in-memory observations, без CH persistence)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.modules.attribution_facts.domain.enums import (
    AttributionCoverageStatus,
    AttributionReasonCode,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionCoverage,
    DayReconciliationResult,
)


@dataclass(frozen=True, slots=True)
class RawNmContributionRow:
    """Одна строка nm/app из raw fullstats до collapse."""

    physical_adv_id: int
    event_date: date
    app_type: int
    ordered_nm_id: int
    orders: int
    gmv_rub: Decimal
    atc: int | None = None
    units_shks: int | None = None


@dataclass(frozen=True, slots=True)
class RawCampaignDayRow:
    """Дневные totals кампании из того же raw payload."""

    physical_adv_id: int
    event_date: date
    orders: int
    gmv_rub: Decimal


@dataclass(frozen=True, slots=True)
class AttributionIngestBatch:
    """Результат ingest на одном fetch chunk (Slice B: без persistence)."""

    shop_id: str
    facts: tuple[AttributionCommerceFact, ...]
    reconciliations: tuple[DayReconciliationResult, ...]
    coverage: AttributionCoverage
    used_raw_apps_nms: bool
    partial_membership_fallback: bool
    reason_codes: tuple[AttributionReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class CollapsedMapperOnlyInput:
    """Маркер ingest только из DayStats без apps/nms."""

    physical_adv_id: int
    event_date: date
    day_orders: int
    day_gmv_rub: Decimal


def coverage_for_ingest_source(
    *,
    has_raw_nm_rows: bool,
    partial_membership_fallback: bool,
    all_days_reconciled: bool,
) -> AttributionCoverage:
    """
    Coverage ingest-источника: collapsed-only не может быть COMPLETE.

    Args:
        has_raw_nm_rows: Есть ли развёрнутые apps/nms строки.
        partial_membership_fallback: Inventory fallback без history.
        all_days_reconciled: Все дни прошли reconciliation.

    Returns:
        AttributionCoverage с fail-closed reason codes.
    """
    reason_codes: list[AttributionReasonCode] = []
    if not has_raw_nm_rows:
        return AttributionCoverage(
            status=AttributionCoverageStatus.PARTIAL,
            reason_codes=(AttributionReasonCode.ATTRIBUTION_SOURCE_PARTIAL,),
        )
    if partial_membership_fallback:
        reason_codes.append(AttributionReasonCode.ATTRIBUTION_SOURCE_PARTIAL)
    if not all_days_reconciled:
        reason_codes.append(AttributionReasonCode.RECONCILIATION_FAILED)
        return AttributionCoverage(
            status=AttributionCoverageStatus.PARTIAL,
            reason_codes=tuple(reason_codes),
        )
    return AttributionCoverage(
        status=AttributionCoverageStatus.COMPLETE,
        reason_codes=tuple(reason_codes),
    )


__all__ = [
    "AttributionIngestBatch",
    "CollapsedMapperOnlyInput",
    "RawCampaignDayRow",
    "RawNmContributionRow",
    "coverage_for_ingest_source",
]
