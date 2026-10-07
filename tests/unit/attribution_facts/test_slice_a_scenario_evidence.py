"""Slice-A scenario evidence (S04, S07, S13, S14) — pure domain only."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.modules.attribution_facts.domain.classification import classify_ordered_nm
from app.modules.attribution_facts.domain.coverage import evaluate_window_coverage
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
    AttributionScope,
    CampaignDaySpendReference,
    DateWindow,
    DayReconciliationResult,
    MembershipSnapshot,
    ObservationProvenance,
)
from app.modules.attribution_facts.testing.in_memory_reader import (
    InMemoryAttributionFactsReader,
)

pytestmark = pytest.mark.unit

_DAY = date(2026, 9, 7)
_PROV = ObservationProvenance(
    observation_id="obs-s04",
    source_revision=1,
    ingested_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
    membership_snapshot_id="snap",
)


def test_s04_missing_membership_is_unknown_not_linked_or_direct() -> None:
    """S04: без membership — только UNKNOWN, без LINKED/DIRECT fallback."""
    result = classify_ordered_nm(14824677, None)
    assert result == AttributionClass.UNKNOWN
    assert result != AttributionClass.LINKED
    assert result != AttributionClass.DIRECT


def test_s04_empty_promoted_set_unknown_not_linked() -> None:
    """S04: пустой promoted set — UNKNOWN, не LINKED."""
    snapshot = MembershipSnapshot(
        snapshot_id="s",
        shop_id="shop",
        physical_adv_id=1,
        event_date=_DAY,
        promoted_nm_ids=frozenset(),
    )
    result = classify_ordered_nm(14824677, snapshot)
    assert result == AttributionClass.UNKNOWN
    assert result != AttributionClass.LINKED


def test_s07_economics_blocked_without_attribution_source() -> None:
    """S07: нет facts/membership evidence → NO_DATA coverage → нет numeric CPO/DRR."""
    window = DateWindow(_DAY, _DAY)
    coverage = evaluate_window_coverage(
        has_any_facts=False,
        all_days_reconciled=True,
        partial_membership_fallback=False,
        source_complete_through=None,
        window=window,
    )
    assert coverage.status == AttributionCoverageStatus.NO_DATA
    spend = (CampaignDaySpendReference(1, _DAY, Decimal(100)),)
    for attr_class in (AttributionClass.DIRECT, AttributionClass.LINKED):
        cpo = compute_cpo_fact(
            f"CPO_FACT_{attr_class}",
            (),
            spend,
            attr_class,
            coverage,
        )
        drr = compute_drr_fact(
            f"DRR_FACT_{attr_class}",
            (),
            spend,
            attr_class,
            coverage,
        )
        assert cpo.value is None
        assert drr.value is None
        assert (
            AttributionReasonCode.BLOCKED_BY_ATTRIBUTION_FACTS in cpo.reason_codes
        )
        assert (
            AttributionReasonCode.BLOCKED_BY_ATTRIBUTION_FACTS in drr.reason_codes
        )


def test_s07_unknown_class_facts_do_not_emit_direct_linked_cpo() -> None:
    """S07: UNKNOWN rows не дают numeric DIRECT/LINKED economics даже при spend."""
    fact = AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="s1",
            physical_adv_id=1,
            event_date=_DAY,
            app_type=1,
            ordered_nm_id=1,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        ),
        metrics=AttributionMetrics(
            attributed_orders=5,
            attributed_gmv_rub=Decimal(500),
        ),
        attribution_class=AttributionClass.UNKNOWN,
        provenance=_PROV,
    )
    cov = AttributionCoverage(status=AttributionCoverageStatus.COMPLETE)
    spend = (CampaignDaySpendReference(1, _DAY, Decimal(50)),)
    cpo_direct = compute_cpo_fact(
        "CPO_FACT_DIRECT", (fact,), spend, AttributionClass.DIRECT, cov
    )
    cpo_linked = compute_cpo_fact(
        "CPO_FACT_LINKED", (fact,), spend, AttributionClass.LINKED, cov
    )
    assert cpo_direct.value is None
    assert cpo_linked.value is None
    assert AttributionReasonCode.DENOMINATOR_ZERO in cpo_direct.reason_codes
    assert AttributionReasonCode.DENOMINATOR_ZERO in cpo_linked.reason_codes


@pytest.mark.asyncio
async def test_s13_reader_partial_coverage_exposes_reason_codes() -> None:
    """S13: in-memory reader возвращает PARTIAL coverage и reason_codes."""
    fact = AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="shop-a",
            physical_adv_id=10,
            event_date=_DAY,
            app_type=1,
            ordered_nm_id=1,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        ),
        metrics=AttributionMetrics(
            attributed_orders=1,
            attributed_gmv_rub=Decimal(1),
        ),
        attribution_class=AttributionClass.DIRECT,
        provenance=_PROV,
    )
    failed_recon = DayReconciliationResult(
        physical_adv_id=10,
        event_date=_DAY,
        passed=False,
        nm_orders_sum=1,
        day_orders=5,
        nm_gmv_sum=Decimal(1),
        day_gmv_rub=Decimal(5),
        unattributed_orders=4,
        reason_codes=(AttributionReasonCode.RECONCILIATION_FAILED,),
    )
    reader = InMemoryAttributionFactsReader(
        facts=(fact,),
        reconciliations=(failed_recon,),
        source_complete_through=_DAY,
    )
    result = await reader.query(
        AttributionScope(shop_id="shop-a", physical_adv_ids=frozenset({10})),
        DateWindow(_DAY, _DAY),
    )
    assert result.coverage.status == AttributionCoverageStatus.PARTIAL
    assert (
        AttributionReasonCode.RECONCILIATION_FAILED
        in result.coverage.reason_codes
    )


def test_s14_package_cutoff_does_not_imply_complete_coverage() -> None:
    """S14: package_cutoff совпадает с window, но source не доказан → PARTIAL."""
    window = DateWindow(_DAY, _DAY)
    coverage = evaluate_window_coverage(
        has_any_facts=True,
        all_days_reconciled=True,
        partial_membership_fallback=False,
        source_complete_through=date(2026, 9, 1),
        window=window,
        package_cutoff_date=_DAY,
    )
    assert coverage.status == AttributionCoverageStatus.PARTIAL
    assert (
        AttributionReasonCode.ATTRIBUTION_SOURCE_PARTIAL
        in coverage.reason_codes
    )
    assert coverage.package_cutoff_date == _DAY
    assert coverage.source_complete_through == date(2026, 9, 1)
