"""Slice D: AttributionFactsReader → AI Package analysis metrics (S15/S16)."""

from __future__ import annotations

from datetime import UTC, date, datetime
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
    CPO_FACT_DIRECT,
    CPO_FACT_LINKED,
)
from app.modules.ai_package_v1.analysis.models import (
    AnalysisAttributionLegEvidence,
    AnalysisBuildRequest,
    CampaignDailyFact,
)
from app.modules.ai_package_v1.analysis.catalog import build_analysis_windows
from app.modules.ai_package_v1.keyword_performance.windows.engine import WindowSpec
from app.modules.ai_package_v1.analysis.service import AnalysisAggregationService
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv

pytestmark = pytest.mark.unit

_DAY = date(2026, 10, 1)
_GENERATED = "2026-10-06T12:00:00Z"
_PROV = ObservationProvenance(
    observation_id="a" * 32,
    source_revision=1,
    ingested_at=datetime(2026, 10, 2, tzinfo=UTC),
    membership_snapshot_id="snap",
)


def _scope() -> tuple[ExportScopeAdv, ...]:
    return (
        ExportScopeAdv(
            shop_id="1",
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="pair",
            active_status="active",
            bot_active=False,
        ),
    )


def _fact(
    adv_id: int,
    *,
    orders: int = 2,
    gmv: Decimal = Decimal("100"),
    attr: AttributionClass = AttributionClass.DIRECT,
    nm: int = 100,
) -> AttributionCommerceFact:
    return AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="shop-1",
            physical_adv_id=adv_id,
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


def _campaign_day(adv_id: int, spend: float = 20.0) -> CampaignDailyFact:
    return CampaignDailyFact(
        adv_id=adv_id,
        stat_date=_DAY,
        views=10,
        clicks=2,
        spend_rub=spend,
        added_to_cart=1,
        orders=4,
        order_sum_rub=80.0,
    )


def _complete_query(*facts: AttributionCommerceFact) -> AttributionQueryResult:
    return AttributionQueryResult(
        facts=facts,
        coverage=AttributionCoverage(
            status=AttributionCoverageStatus.COMPLETE,
            source_complete_through=_DAY,
        ),
        reconciliations=(),
    )


def _partial_query() -> AttributionQueryResult:
    return AttributionQueryResult(
        facts=(),
        coverage=AttributionCoverage(
            status=AttributionCoverageStatus.PARTIAL,
            reason_codes=(AttributionReasonCode.RECONCILIATION_FAILED,),
        ),
    )


def _analysis_windows() -> list[WindowSpec]:
    period = ExportPeriod(start=_DAY, end=_DAY)
    cutoff = PackageCutoff.from_generated_at(_GENERATED)
    return build_analysis_windows(
        cutoff,
        campaign_first=_DAY,
        campaign_last=_DAY,
        requested_period=period,
    )


def _evidence_for_legs(
    adv_id: int,
    query: AttributionQueryResult,
) -> tuple[AnalysisAttributionLegEvidence, ...]:
    windows = _analysis_windows()
    covering = next(
        (spec for spec in windows if spec.window_id == "requested_custom"),
        next(
            (spec for spec in windows if spec.start <= _DAY <= spec.end),
            windows[0],
        ),
    )
    return (
        AnalysisAttributionLegEvidence(
            window_id=str(covering.window_id),
            physical_adv_id=adv_id,
            query_result=query,
        ),
    )


def _build(
    evidence: tuple[AnalysisAttributionLegEvidence, ...],
    campaign_facts: tuple[CampaignDailyFact, ...],
) -> list[dict[str, object]]:
    period = ExportPeriod(start=_DAY, end=_DAY)
    result = AnalysisAggregationService().build(
        AnalysisBuildRequest(
            shop_id="shop-1",
            generated_at=_GENERATED,
            period=period,
            scope=_scope(),
            campaign_facts=campaign_facts,
            campaign_source_complete_through=_DAY,
            attribution_by_leg_window=evidence,
        )
    )
    return result.campaign_rows


def _leg_row(
    rows: list[dict[str, object]],
    adv_id: int,
    *,
    window_id: str | None = None,
) -> dict[str, object]:
    candidates = [
        row
        for row in rows
        if row.get("adv_id") == adv_id
        and (window_id is None or row.get("window_id") == window_id)
    ]
    for row in candidates:
        metrics = row.get("metrics")
        if isinstance(metrics, dict) and ATTRIBUTION_DIRECT_ORDERS in metrics:
            return row
        uncomputable = row.get("uncomputable")
        if isinstance(uncomputable, list) and any(
            isinstance(item, dict)
            and cast(dict[str, object], item).get("metric_id")
            in {CPO_FACT_DIRECT, ATTRIBUTION_DIRECT_ORDERS}
            for item in cast(list[object], uncomputable)
        ):
            return row
    return candidates[0]


def _metrics_of(row: dict[str, object]) -> dict[str, object]:
    metrics = row.get("metrics")
    assert isinstance(metrics, dict)
    return cast(dict[str, object], metrics)


def _metric(row: dict[str, object], metric_id: str) -> object | None:
    cell = _metrics_of(row).get(metric_id)
    if not isinstance(cell, dict):
        return None
    cell_dict = cast(dict[str, object], cell)
    return cell_dict.get("value")


def _has_uncomputable(row: dict[str, object], metric_id: str, reason: str) -> bool:
    uncomputable = row.get("uncomputable")
    if not isinstance(uncomputable, list):
        return False
    for item in cast(list[object], uncomputable):
        if not isinstance(item, dict):
            continue
        entry = cast(dict[str, object], item)
        if entry.get("metric_id") != metric_id:
            continue
        codes = entry.get("reason_codes")
        if isinstance(codes, list) and reason in cast(list[object], codes):
            return True
    return False


def test_s15_complete_direct_and_linked_metrics_emitted() -> None:
    evidence = _evidence_for_legs(
        111,
        _complete_query(
            _fact(111, orders=4, gmv=Decimal("200"), attr=AttributionClass.DIRECT),
            _fact(111, orders=1, gmv=Decimal("50"), attr=AttributionClass.LINKED, nm=200),
        ),
    )
    rows = _build(evidence, (_campaign_day(111, 40.0),))
    row = _leg_row(rows, 111, window_id=evidence[0].window_id)
    assert _metric(row, ATTRIBUTION_DIRECT_ORDERS) == 4
    assert _metric(row, CPO_FACT_DIRECT) == 10.0
    assert _metric(row, CPO_FACT_LINKED) == 40.0


def test_partial_blocks_numeric_cpo() -> None:
    evidence = _evidence_for_legs(111, _partial_query())
    rows = _build(evidence, (_campaign_day(111),))
    row = _leg_row(rows, 111, window_id=evidence[0].window_id)
    assert _metric(row, CPO_FACT_DIRECT) is None
    raw_uncomputable = row.get("uncomputable", [])
    assert isinstance(raw_uncomputable, list)
    blocked: list[dict[str, object]] = [
        cast(dict[str, object], item)
        for item in cast(list[object], raw_uncomputable)
        if isinstance(item, dict)
        and cast(dict[str, object], item).get("metric_id") == CPO_FACT_DIRECT
    ]
    assert blocked


def test_no_linked_fallback_when_linked_unknown() -> None:
    evidence = _evidence_for_legs(
        111,
        _complete_query(
            _fact(111, orders=2, gmv=Decimal("100"), attr=AttributionClass.DIRECT),
        ),
    )
    rows = _build(evidence, (_campaign_day(111),))
    row = _leg_row(rows, 111, window_id=evidence[0].window_id)
    assert _metric(row, CPO_FACT_DIRECT) is not None
    assert _metric(row, CPO_FACT_LINKED) is None
    assert _has_uncomputable(row, CPO_FACT_LINKED, "ATTRIBUTION_RELATION_UNKNOWN")


def test_s16_package_scope_attribution_scope_mismatch() -> None:
    evidence = (
        *_evidence_for_legs(111, _complete_query(_fact(111))),
        *_evidence_for_legs(222, _complete_query(_fact(222))),
    )
    period = ExportPeriod(start=_DAY, end=_DAY)
    result = AnalysisAggregationService().build(
        AnalysisBuildRequest(
            shop_id="shop-1",
            generated_at=_GENERATED,
            period=period,
            scope=_scope(),
            campaign_facts=(_campaign_day(111), _campaign_day(222)),
            attribution_by_leg_window=evidence,
        )
    )
    package = next(
        row for row in result.package_rows if row.get("entity_kind") == "PACKAGE_CAMPAIGN_SCOPE"
    )
    assert _has_uncomputable(package, CPO_FACT_DIRECT, "ATTRIBUTION_SCOPE_MISMATCH")


def test_deterministic_repeatable_build() -> None:
    evidence = _evidence_for_legs(111, _complete_query(_fact(111)))
    facts = (_campaign_day(111),)
    first = _build(evidence, facts)
    second = _build(evidence, facts)
    assert first == second
