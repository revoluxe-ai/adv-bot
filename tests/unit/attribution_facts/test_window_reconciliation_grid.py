"""Fail-closed reconciliation grid coverage (Slice C certification)."""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.attribution_facts.domain.coverage import evaluate_window_coverage
from app.modules.attribution_facts.domain.enums import AttributionCoverageStatus
from app.modules.attribution_facts.domain.models import (
    AttributionScope,
    DateWindow,
    DayReconciliationResult,
)
from app.modules.attribution_facts.domain.window_reconciliation_coverage import (
    assess_reconciliation_grid,
)

pytestmark = pytest.mark.unit

_START = date(2026, 9, 1)
_END = date(2026, 9, 7)
_WINDOW = DateWindow(_START, _END)
_SCOPE = AttributionScope(shop_id="s1", physical_adv_ids=frozenset({100}))


def _recon(adv_id: int, day: date, passed: bool = True) -> DayReconciliationResult:
    from decimal import Decimal

    return DayReconciliationResult(
        physical_adv_id=adv_id,
        event_date=day,
        passed=passed,
        nm_orders_sum=1,
        day_orders=1,
        nm_gmv_sum=Decimal("1"),
        day_gmv_rub=Decimal("1"),
        unattributed_orders=0,
    )


def test_a_sparse_one_pass_day_not_complete() -> None:
    """7-day window with only one PASS day → grid fail."""
    rows = (_recon(100, _START),)
    ok, through = assess_reconciliation_grid(rows, _SCOPE, _WINDOW)
    assert not ok
    assert through is None


def test_b_two_adv_ids_one_missing_recon_not_complete() -> None:
    """Two physical adv ids; one lacks reconciliation → fail."""
    scope = AttributionScope(shop_id="s1", physical_adv_ids=frozenset({100, 200}))
    rows = tuple(_recon(100, day) for day in (_START, _END))
    ok, through = assess_reconciliation_grid(rows, scope, _WINDOW)
    assert not ok
    assert through is None


def test_c_full_matrix_pass_may_complete() -> None:
    """All scope×day cells PASS → grid pass and evidence through window.end."""
    rows: list[DayReconciliationResult] = []
    day = _START
    while day <= _END:
        rows.append(_recon(100, day))
        day = date.fromordinal(day.toordinal() + 1)
    ok, through = assess_reconciliation_grid(tuple(rows), _SCOPE, _WINDOW)
    assert ok
    assert through == _END
    cov = evaluate_window_coverage(
        has_any_facts=True,
        all_days_reconciled=ok,
        partial_membership_fallback=False,
        source_complete_through=through,
        window=_WINDOW,
    )
    assert cov.status == AttributionCoverageStatus.COMPLETE


def test_d_one_required_recon_fail_not_complete() -> None:
    """One required reconciliation FAIL → not complete."""
    rows: list[DayReconciliationResult] = []
    day = _START
    while day <= _END:
        passed = day != date(2026, 9, 3)
        rows.append(_recon(100, day, passed=passed))
        day = date.fromordinal(day.toordinal() + 1)
    ok, _ = assess_reconciliation_grid(tuple(rows), _SCOPE, _WINDOW)
    assert not ok


def test_e_facts_without_recon_grid_fails_reader_path() -> None:
    """Empty reconciliation set cannot satisfy required grid."""
    ok, through = assess_reconciliation_grid((), _SCOPE, _WINDOW)
    assert not ok
    assert through is None
