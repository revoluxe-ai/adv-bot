"""Модель покрытия attribution facts (fail-closed, package cutoff ≠ COMPLETE)."""

from __future__ import annotations

from datetime import date

from app.modules.attribution_facts.domain.enums import (
    AttributionCoverageStatus,
    AttributionReasonCode,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCoverage,
    DateWindow,
    DayReconciliationResult,
)


def package_cutoff_does_not_imply_complete(
    package_cutoff_date: date,
    source_complete_through: date | None,
    window: DateWindow,
) -> bool:
    """
    True если cutoff совпадает с концом окна, но источник не доказал полноту.

    Используется потребителями, чтобы не выставлять COMPLETE по cutoff alone.
    """
    if source_complete_through is None:
        return window.end <= package_cutoff_date
    return window.end <= package_cutoff_date and window.end > source_complete_through


def evaluate_window_coverage(
    *,
    has_any_facts: bool,
    all_days_reconciled: bool,
    partial_membership_fallback: bool,
    source_complete_through: date | None,
    window: DateWindow,
    package_cutoff_date: date | None = None,
) -> AttributionCoverage:
    """
    Оценить coverage status для окна (pure, без IO).

    Args:
        has_any_facts: Есть ли хотя бы один fact в scope/window.
        all_days_reconciled: Все дни окна прошли reconciliation PASS.
        partial_membership_fallback: Использовался inventory fallback.
        source_complete_through: Последний доказанный полный день источника.
        window: Запрошенное окно.
        package_cutoff_date: Номинальная граница пакета (не доказательство).

    Returns:
        AttributionCoverage с reason codes.
    """
    reason_codes: list[AttributionReasonCode] = []
    if not has_any_facts:
        return AttributionCoverage(
            status=AttributionCoverageStatus.NO_DATA,
            reason_codes=(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING,),
            source_complete_through=source_complete_through,
            effective_covered_range_start=window.start,
            effective_covered_range_end=window.end,
            package_cutoff_date=package_cutoff_date,
        )
    if partial_membership_fallback:
        reason_codes.append(AttributionReasonCode.ATTRIBUTION_SOURCE_PARTIAL)
    if not all_days_reconciled:
        reason_codes.append(AttributionReasonCode.RECONCILIATION_FAILED)
        return AttributionCoverage(
            status=AttributionCoverageStatus.PARTIAL,
            reason_codes=tuple(reason_codes),
            source_complete_through=source_complete_through,
            effective_covered_range_start=window.start,
            effective_covered_range_end=window.end,
            package_cutoff_date=package_cutoff_date,
        )
    if package_cutoff_date is not None and package_cutoff_does_not_imply_complete(
        package_cutoff_date, source_complete_through, window
    ):
        reason_codes.append(AttributionReasonCode.ATTRIBUTION_SOURCE_PARTIAL)
        return AttributionCoverage(
            status=AttributionCoverageStatus.PARTIAL,
            reason_codes=tuple(reason_codes),
            source_complete_through=source_complete_through,
            effective_covered_range_start=window.start,
            effective_covered_range_end=window.end,
            package_cutoff_date=package_cutoff_date,
        )
    if partial_membership_fallback:
        return AttributionCoverage(
            status=AttributionCoverageStatus.PARTIAL,
            reason_codes=tuple(reason_codes),
            source_complete_through=source_complete_through,
            effective_covered_range_start=window.start,
            effective_covered_range_end=window.end,
            package_cutoff_date=package_cutoff_date,
        )
    return AttributionCoverage(
        status=AttributionCoverageStatus.COMPLETE,
        reason_codes=tuple(reason_codes),
        source_complete_through=source_complete_through,
        effective_covered_range_start=window.start,
        effective_covered_range_end=window.end,
        package_cutoff_date=package_cutoff_date,
    )


def all_reconciliations_passed(
    reconciliations: tuple[DayReconciliationResult, ...],
) -> bool:
    """True если каждая дневная сверка в окне прошла."""
    if not reconciliations:
        return False
    return all(item.passed for item in reconciliations)


def can_emit_direct_linked_economics(coverage: AttributionCoverage) -> bool:
    """Numeric DIRECT/LINKED CPO/DRR разрешены только при COMPLETE coverage."""
    return coverage.status == AttributionCoverageStatus.COMPLETE
