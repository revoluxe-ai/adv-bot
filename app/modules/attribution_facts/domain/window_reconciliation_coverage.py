"""Fail-closed оценка полноты reconciliation grid для scope/window."""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.attribution_facts.domain.models import (
    AttributionScope,
    DateWindow,
    DayReconciliationResult,
)


def iter_required_reconciliation_cells(
    scope: AttributionScope,
    window: DateWindow,
) -> tuple[tuple[int, date], ...]:
    """Каждая ячейка physical_adv_id × event_date в окне (inclusive)."""
    cells: list[tuple[int, date]] = []
    day = window.start
    while day <= window.end:
        for adv_id in sorted(scope.physical_adv_ids):
            cells.append((adv_id, day))
        day += timedelta(days=1)
    return tuple(cells)


def assess_reconciliation_grid(
    reconciliations: tuple[DayReconciliationResult, ...],
    scope: AttributionScope,
    window: DateWindow,
) -> tuple[bool, date | None]:
    """
    Вернуть (all_required_pass, evidence_source_complete_through).

    COMPLETE требует PASS для каждой required ячейки; иначе fail-closed.
    source_complete_through — max event_date при полном покрытии, иначе None.
    """
    required = iter_required_reconciliation_cells(scope, window)
    if not required:
        return False, None
    by_cell: dict[tuple[int, date], DayReconciliationResult] = {}
    for item in reconciliations:
        by_cell[(item.physical_adv_id, item.event_date)] = item
    for cell in required:
        row = by_cell.get(cell)
        if row is None or not row.passed:
            return False, None
    return True, window.end


__all__ = ["assess_reconciliation_grid", "iter_required_reconciliation_cells"]
