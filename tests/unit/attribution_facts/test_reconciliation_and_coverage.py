"""Unit-тесты reconciliation, coverage и derived metrics."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.modules.attribution_facts.domain.classification import classify_ordered_nm
from app.modules.attribution_facts.domain.coverage import (
    can_emit_direct_linked_economics,
    evaluate_window_coverage,
    package_cutoff_does_not_imply_complete,
)
from app.modules.attribution_facts.domain.derived_metrics import (
    compute_cpo_fact,
    compute_drr_fact,
)
from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
    AttributionReasonCode,
    SourceFamily,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionCoverage,
    AttributionFactKey,
    AttributionMetrics,
    CampaignDaySpendReference,
    CampaignDayTotals,
    DateWindow,
    MembershipSnapshot,
    NmDayContribution,
    ObservationProvenance,
)
from app.modules.attribution_facts.domain.reconciliation import reconcile_campaign_day
from app.modules.attribution_facts.domain.versioning import (
    apply_latest_metrics,
    select_latest_fact,
)

pytestmark = pytest.mark.unit

_DAY = date(2026, 9, 7)
_PROV = ObservationProvenance(
    observation_id="obs-1",
    source_revision=1,
    ingested_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
    membership_snapshot_id="snap-1",
)


def test_reconciliation_pass() -> None:
    """Nm sums совпадают с day totals."""
    day = CampaignDayTotals(
        physical_adv_id=1, event_date=_DAY, orders=5, gmv_rub=Decimal(500)
    )
    rows = (
        NmDayContribution(1, 100, 3, Decimal(300)),
        NmDayContribution(1, 200, 2, Decimal(200)),
    )
    result = reconcile_campaign_day(day, rows)
    assert result.passed
    assert result.unattributed_orders == 0


def test_reconciliation_gap_fail() -> None:
    """Расхождение orders → RECONCILIATION_FAILED и unattributed."""
    day = CampaignDayTotals(
        physical_adv_id=1, event_date=_DAY, orders=5, gmv_rub=Decimal(500)
    )
    rows = (NmDayContribution(1, 100, 2, Decimal(200)),)
    result = reconcile_campaign_day(day, rows)
    assert not result.passed
    assert AttributionReasonCode.RECONCILIATION_FAILED in result.reason_codes
    assert result.unattributed_orders == 3


def test_package_cutoff_not_complete() -> None:
    """Cutoff совпадает с window end, но source не доказан."""
    window = DateWindow(_DAY, _DAY)
    assert package_cutoff_does_not_imply_complete(_DAY, date(2026, 9, 1), window)


def test_coverage_complete_requires_reconciliation() -> None:
    """PARTIAL при failed reconciliation."""
    window = DateWindow(_DAY, _DAY)
    cov = evaluate_window_coverage(
        has_any_facts=True,
        all_days_reconciled=False,
        partial_membership_fallback=False,
        source_complete_through=_DAY,
        window=window,
    )
    assert cov.status == AttributionCoverageStatus.PARTIAL


def test_missing_facts_no_data_not_zero() -> None:
    """NO_DATA при отсутствии facts."""
    window = DateWindow(_DAY, _DAY)
    cov = evaluate_window_coverage(
        has_any_facts=False,
        all_days_reconciled=True,
        partial_membership_fallback=False,
        source_complete_through=None,
        window=window,
    )
    assert cov.status == AttributionCoverageStatus.NO_DATA


def _fact(
    adv_id: int,
    nm_id: int,
    orders: int | None,
    gmv: Decimal | None,
    attr: AttributionClass,
) -> AttributionCommerceFact:
    return AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="s1",
            physical_adv_id=adv_id,
            event_date=_DAY,
            app_type=1,
            ordered_nm_id=nm_id,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        ),
        metrics=AttributionMetrics(
            attributed_orders=orders,
            attributed_gmv_rub=gmv,
        ),
        attribution_class=attr,
        provenance=_PROV,
    )


def test_physical_adv_ids_remain_distinct() -> None:
    """Fact keys различаются по physical_adv_id (Auto vs Search)."""
    f_auto = _fact(10, 1, 1, Decimal(100), AttributionClass.DIRECT)
    f_search = _fact(20, 1, 1, Decimal(100), AttributionClass.DIRECT)
    assert f_auto.key != f_search.key
    assert f_auto.key.physical_adv_id == 10
    assert f_search.key.physical_adv_id == 20


def test_fact_key_excludes_advertised_nm() -> None:
    """Ключ содержит только ordered_nm_id."""
    key = AttributionFactKey(
        shop_id="s1",
        physical_adv_id=1,
        event_date=_DAY,
        app_type=1,
        ordered_nm_id=999,
    )
    assert key.ordered_nm_id == 999
    assert not hasattr(key, "advertised_nm_id")


def test_denominator_zero_cpo() -> None:
    """CPO absent + DENOMINATOR_ZERO при нулевых direct orders."""
    coverage = AttributionCoverage(status=AttributionCoverageStatus.COMPLETE)
    facts = (_fact(1, 1, 0, Decimal(0), AttributionClass.DIRECT),)
    spend = (
        CampaignDaySpendReference(1, _DAY, Decimal(100)),
    )
    result = compute_cpo_fact("CPO_FACT_DIRECT", facts, spend, AttributionClass.DIRECT, coverage)
    assert result.value is None
    assert AttributionReasonCode.DENOMINATOR_ZERO in result.reason_codes


def test_blocked_economics_when_not_complete() -> None:
    """Fail-closed CPO при не-COMPLETE coverage."""
    coverage = AttributionCoverage(status=AttributionCoverageStatus.PARTIAL)
    facts = (_fact(1, 1, 2, Decimal(200), AttributionClass.DIRECT),)
    spend = (CampaignDaySpendReference(1, _DAY, Decimal(100)),)
    result = compute_cpo_fact("CPO_FACT_DIRECT", facts, spend, AttributionClass.DIRECT, coverage)
    assert result.value is None
    assert not can_emit_direct_linked_economics(coverage)


def test_drr_direct_linked() -> None:
    """DRR вычисляется при COMPLETE и ненулевом GMV."""
    coverage = AttributionCoverage(status=AttributionCoverageStatus.COMPLETE)
    facts = (
        _fact(1, 1, 2, Decimal(200), AttributionClass.DIRECT),
        _fact(1, 2, 1, Decimal(100), AttributionClass.LINKED),
    )
    spend = (CampaignDaySpendReference(1, _DAY, Decimal(30)),)
    d_direct = compute_drr_fact(
        "DRR_FACT_DIRECT", facts, spend, AttributionClass.DIRECT, coverage
    )
    d_linked = compute_drr_fact(
        "DRR_FACT_LINKED", facts, spend, AttributionClass.LINKED, coverage
    )
    assert d_direct.value == Decimal(30) / Decimal(200)
    assert d_linked.value == Decimal(30) / Decimal(100)


def test_revision_replaces_not_sums() -> None:
    """Latest observation заменяет prior."""
    base = _fact(1, 1, 1, Decimal(100), AttributionClass.DIRECT)
    newer_prov = ObservationProvenance(
        observation_id="obs-2",
        source_revision=2,
        ingested_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
        membership_snapshot_id="snap-1",
    )
    newer = AttributionCommerceFact(
        key=base.key,
        metrics=AttributionMetrics(attributed_orders=3, attributed_gmv_rub=Decimal(300)),
        attribution_class=AttributionClass.DIRECT,
        provenance=newer_prov,
    )
    latest = select_latest_fact((base, newer))
    assert latest is not None
    assert latest.metrics.attributed_orders == 3
    merged = apply_latest_metrics(base, newer)
    assert merged.metrics.attributed_orders == 3


def test_membership_drives_classification_not_advertised_nm() -> None:
    """Классификация по snapshot, не по одному advertised sku."""
    snap = MembershipSnapshot(
        snapshot_id="s",
        shop_id="s1",
        physical_adv_id=1,
        event_date=_DAY,
        promoted_nm_ids=frozenset({111, 222}),
    )
    assert classify_ordered_nm(111, snap) == AttributionClass.DIRECT
    assert classify_ordered_nm(333, snap) == AttributionClass.LINKED
