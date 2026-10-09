"""Slice D regression matrix: spend gate + independent CPO/DRR denominators."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import cast

import pytest

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
    AttributionQueryResult,
    ObservationProvenance,
)
from app.modules.ai_package_v1.analysis.attribution_evidence import (
    ATTRIBUTION_DIRECT_ORDERS,
    ATTRIBUTION_LINKED_GMV_RUB,
    ATTRIBUTION_LINKED_ORDERS,
    CPO_FACT_DIRECT,
    CPO_FACT_LINKED,
    DRR_FACT_DIRECT,
    DRR_FACT_LINKED,
    assess_campaign_spend_for_economics,
    build_leg_attribution_outputs,
)
from app.modules.ai_package_v1.analysis.constants import CAMPAIGN_SPEND_INCOMPLETE
from app.modules.ai_package_v1.analysis.models import CampaignDailyFact
from app.modules.attribution_facts.domain.derived_metrics import compute_cpo_fact

pytestmark = pytest.mark.unit

_DAY = date(2026, 10, 1)
_END = date(2026, 10, 3)
_PROV = ObservationProvenance(
    observation_id="b" * 32,
    source_revision=1,
    ingested_at=datetime(2026, 10, 2, tzinfo=UTC),
    membership_snapshot_id="snap",
)
_COVERAGE = AttributionCoverage(
    status=AttributionCoverageStatus.COMPLETE,
    source_complete_through=_END,
)


def _fact(
    attr: AttributionClass,
    orders: int | None,
    gmv: Decimal | None,
    nm: int = 100,
) -> AttributionCommerceFact:
    return AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="s",
            physical_adv_id=111,
            event_date=_DAY,
            app_type=1,
            ordered_nm_id=nm,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        ),
        metrics=AttributionMetrics(
            attributed_orders=orders,
            attributed_gmv_rub=gmv,
        ),
        attribution_class=attr,
        provenance=_PROV,
    )


def _campaign(adv_id: int, day: date, spend: float | None) -> CampaignDailyFact:
    return CampaignDailyFact(
        adv_id=adv_id,
        stat_date=day,
        views=1,
        clicks=1,
        spend_rub=spend,
        added_to_cart=0,
        orders=1,
        order_sum_rub=10.0,
    )


def _days(adv_id: int, spend: float = 10.0) -> list[CampaignDailyFact]:
    rows: list[CampaignDailyFact] = []
    day = _DAY
    while day <= _END:
        rows.append(_campaign(adv_id, day, spend))
        day += timedelta(days=1)
    return rows


def _query(*facts: AttributionCommerceFact) -> AttributionQueryResult:
    return AttributionQueryResult(
        facts=facts,
        coverage=_COVERAGE,
        reconciliations=(),
    )


def _metric(metrics: dict[str, object], mid: str) -> object | None:
    cell = metrics.get(mid)
    if not isinstance(cell, dict):
        return None
    cell_dict = cast(dict[str, object], cell)
    return cell_dict.get("value")


def _reasons(uncomputable: list[dict[str, object]], mid: str) -> list[str]:
    for item in uncomputable:
        if item.get("metric_id") != mid:
            continue
        codes = item.get("reason_codes")
        if not isinstance(codes, list):
            return []
        out: list[str] = []
        for code in cast(list[object], codes):
            if isinstance(code, AttributionReasonCode):
                out.append(str(code))
            elif isinstance(code, str):
                out.append(code)
        return out
    return []


def test_a_complete_attribution_and_spend_emits_cpo_drr() -> None:
    facts = (
        _fact(AttributionClass.DIRECT, 2, Decimal("100")),
        _fact(AttributionClass.LINKED, 1, Decimal("50"), nm=200),
    )
    campaign = _days(111, 30.0)
    metrics, _gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, CPO_FACT_DIRECT) == 45.0  # 90/2
    assert _metric(metrics, DRR_FACT_DIRECT) == 0.9
    assert _metric(metrics, ATTRIBUTION_DIRECT_ORDERS) == 2


def test_b_partial_campaign_blocks_only_economics() -> None:
    facts = (_fact(AttributionClass.DIRECT, 2, Decimal("100")),)
    campaign = _days(111)
    metrics, gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="PARTIAL",
    )
    assert _metric(metrics, ATTRIBUTION_DIRECT_ORDERS) == 2
    assert _metric(metrics, CPO_FACT_DIRECT) is None
    assert CAMPAIGN_SPEND_INCOMPLETE in _reasons(gaps, CPO_FACT_DIRECT)


def test_c_missing_spend_not_zero() -> None:
    campaign = _days(111)
    campaign[1] = _campaign(111, date(2026, 10, 2), None)
    metrics, gaps = build_leg_attribution_outputs(
        _query(_fact(AttributionClass.DIRECT, 2, Decimal("100"))),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, CPO_FACT_DIRECT) is None
    assert CAMPAIGN_SPEND_INCOMPLETE in _reasons(gaps, CPO_FACT_DIRECT)


def test_d_orders_missing_gmv_present_drr_only() -> None:
    facts = (_fact(AttributionClass.DIRECT, None, Decimal("100")),)
    campaign = _days(111, 20.0)
    metrics, _gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, CPO_FACT_DIRECT) is None
    assert _metric(metrics, DRR_FACT_DIRECT) == 0.6  # 60 rub spend / 100 GMV (3-day window)


def test_e_orders_present_gmv_missing_cpo_only() -> None:
    facts = (_fact(AttributionClass.DIRECT, 2, None),)
    campaign = _days(111, 20.0)
    metrics, gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, CPO_FACT_DIRECT) == 30.0
    assert _metric(metrics, DRR_FACT_DIRECT) is None
    assert AttributionReasonCode.DENOMINATOR_ZERO not in _reasons(gaps, DRR_FACT_DIRECT)


def test_f_zero_orders_nonzero_gmv() -> None:
    facts = (_fact(AttributionClass.DIRECT, 0, Decimal("100")),)
    campaign = _days(111, 10.0)
    metrics, gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, CPO_FACT_DIRECT) is None
    assert AttributionReasonCode.DENOMINATOR_ZERO in _reasons(gaps, CPO_FACT_DIRECT)
    assert _metric(metrics, DRR_FACT_DIRECT) == 0.3  # 30 rub spend / 100 GMV


def test_g_orders_present_gmv_zero_drr_denominator_zero() -> None:
    facts = (_fact(AttributionClass.DIRECT, 2, Decimal("0")),)
    campaign = _days(111, 10.0)
    metrics, gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, CPO_FACT_DIRECT) == 15.0
    assert _metric(metrics, DRR_FACT_DIRECT) is None
    assert AttributionReasonCode.DENOMINATOR_ZERO in _reasons(gaps, DRR_FACT_DIRECT)


def test_h_linked_independent_denominators() -> None:
    facts = (_fact(AttributionClass.LINKED, None, Decimal("80"), nm=200),)
    campaign = _days(111, 10.0)
    metrics, gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, CPO_FACT_LINKED) is None
    assert AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN in _reasons(
        gaps, CPO_FACT_LINKED
    )
    assert _metric(metrics, DRR_FACT_LINKED) == 0.375
    assert _metric(metrics, ATTRIBUTION_LINKED_GMV_RUB) == 80


def test_j_no_linked_rows_blocks_linked_not_direct() -> None:
    facts = (_fact(AttributionClass.DIRECT, 1, Decimal("50")),)
    campaign = _days(111, 10.0)
    metrics, gaps = build_leg_attribution_outputs(
        _query(*facts),
        physical_adv_id=111,
        window_start=_DAY,
        window_end=_END,
        campaign_facts_in_window=campaign,
        campaign_coverage_status="COMPLETE",
    )
    assert _metric(metrics, ATTRIBUTION_DIRECT_ORDERS) == 1
    assert _metric(metrics, ATTRIBUTION_LINKED_ORDERS) is None
    assert AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN in _reasons(
        gaps, ATTRIBUTION_LINKED_ORDERS
    )
    assert _metric(metrics, CPO_FACT_DIRECT) == 30.0
    assert _metric(metrics, CPO_FACT_LINKED) is None


def test_i_partial_nm_sum_fails_closed() -> None:
    facts = (
        _fact(AttributionClass.DIRECT, 1, Decimal("50"), nm=1),
        _fact(AttributionClass.DIRECT, None, Decimal("50"), nm=2),
    )
    spend_refs = tuple(
        assess_campaign_spend_for_economics(
            physical_adv_id=111,
            window_start=_DAY,
            window_end=_DAY,
            campaign_facts_in_window=[_campaign(111, _DAY, 10.0)],
            campaign_coverage_status="COMPLETE",
        )[1]
    )
    cpo = compute_cpo_fact(
        CPO_FACT_DIRECT, facts, spend_refs, AttributionClass.DIRECT, _COVERAGE
    )
    assert cpo.value is None
    assert AttributionReasonCode.DENOMINATOR_ZERO not in cpo.reason_codes
