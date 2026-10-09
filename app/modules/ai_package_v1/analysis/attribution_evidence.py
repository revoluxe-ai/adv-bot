"""Attribution facts → analysis metrics (domain formulas, fail-closed)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.modules.attribution_facts.domain.coverage import can_emit_direct_linked_economics
from app.modules.attribution_facts.domain.derived_metrics import (
    compute_cpo_fact,
    compute_drr_fact,
)
from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
    AttributionReasonCode,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionCoverage,
    AttributionQueryResult,
    CampaignDaySpendReference,
)
from app.modules.ai_package_v1.analysis.constants import (
    ATTRIBUTION_BLOCKERS,
    CAMPAIGN_SPEND_INCOMPLETE,
    METRIC_DEFINITION_VERSION,
)
from app.modules.ai_package_v1.analysis.models import CampaignDailyFact

ATTRIBUTION_DIRECT_ORDERS = "ATTRIBUTION_DIRECT_ORDERS"
ATTRIBUTION_DIRECT_GMV_RUB = "ATTRIBUTION_DIRECT_GMV_RUB"
ATTRIBUTION_LINKED_ORDERS = "ATTRIBUTION_LINKED_ORDERS"
ATTRIBUTION_LINKED_GMV_RUB = "ATTRIBUTION_LINKED_GMV_RUB"

CPO_FACT_DIRECT = "CPO_FACT_DIRECT"
CPO_FACT_LINKED = "CPO_FACT_LINKED"
DRR_FACT_DIRECT = "DRR_FACT_DIRECT"
DRR_FACT_LINKED = "DRR_FACT_LINKED"

_ECON_METRIC_IDS: tuple[str, ...] = (
    CPO_FACT_DIRECT,
    CPO_FACT_LINKED,
    DRR_FACT_DIRECT,
    DRR_FACT_LINKED,
)

_ATTRIBUTION_METRIC_IDS: tuple[str, ...] = (
    ATTRIBUTION_DIRECT_ORDERS,
    ATTRIBUTION_DIRECT_GMV_RUB,
    ATTRIBUTION_LINKED_ORDERS,
    ATTRIBUTION_LINKED_GMV_RUB,
    *_ECON_METRIC_IDS,
)


def _iter_window_days(start: date, end: date) -> tuple[date, ...]:
    days: list[date] = []
    day = start
    while day <= end:
        days.append(day)
        day += timedelta(days=1)
    return tuple(days)


def assess_campaign_spend_for_economics(
    *,
    physical_adv_id: int,
    window_start: date,
    window_end: date,
    campaign_facts_in_window: list[CampaignDailyFact],
    campaign_coverage_status: str,
) -> tuple[bool, tuple[CampaignDaySpendReference, ...]]:
    """
    Spend numerator для attribution CPO/DRR: полный factual spend по дням окна.

    Fail-closed: PARTIAL/NO_DATA campaign coverage или пропуск spend_rub → incomplete.
    """
    if campaign_coverage_status != "COMPLETE":
        return False, ()
    by_day: dict[date, CampaignDailyFact] = {
        fact.stat_date: fact
        for fact in campaign_facts_in_window
        if fact.adv_id == physical_adv_id
    }
    refs: list[CampaignDaySpendReference] = []
    for day in _iter_window_days(window_start, window_end):
        row = by_day.get(day)
        if row is None or row.spend_rub is None:
            return False, ()
        refs.append(
            CampaignDaySpendReference(
                physical_adv_id=physical_adv_id,
                event_date=day,
                spend_rub=Decimal(str(row.spend_rub)),
            )
        )
    return True, tuple(refs)


def _sum_class(
    facts: tuple[AttributionCommerceFact, ...],
    attr_class: AttributionClass,
    *,
    orders: bool,
) -> int | Decimal | None:
    total_orders = 0
    total_gmv = Decimal(0)
    saw_class_row = False
    for fact in facts:
        if fact.attribution_class != attr_class:
            continue
        saw_class_row = True
        if orders:
            if fact.metrics.attributed_orders is None:
                return None
            total_orders += fact.metrics.attributed_orders
        else:
            if fact.metrics.attributed_gmv_rub is None:
                return None
            total_gmv += fact.metrics.attributed_gmv_rub
    if not saw_class_row:
        return None
    return total_orders if orders else total_gmv


def _metric_cell(value: int | float | Decimal) -> dict[str, object]:
    encoded: int | float
    if isinstance(value, Decimal):
        encoded = float(value)
    else:
        encoded = value
    return {
        "value": encoded,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "scope_note": "attribution-scoped factual metric from AttributionFactsReader",
    }


def _uncomputable(metric_id: str, reason_codes: tuple[str, ...]) -> dict[str, object]:
    return {"metric_id": metric_id, "reason_codes": list(reason_codes)}


def _map_reason(code: AttributionReasonCode) -> str:
    return str(code)


def _block_economics(
    uncomputable: list[dict[str, object]],
    metric_ids: tuple[str, ...],
    reason: str,
) -> None:
    for metric_id in metric_ids:
        uncomputable.append(_uncomputable(metric_id, (reason,)))


def build_leg_attribution_outputs(
    query: AttributionQueryResult,
    *,
    physical_adv_id: int,
    window_start: date,
    window_end: date,
    campaign_facts_in_window: list[CampaignDailyFact],
    campaign_coverage_status: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """
    Metrics/uncomputable для одной physical leg × окно.

    Count metrics при COMPLETE attribution; CPO/DRR additionally require complete spend.
    """
    metrics: dict[str, object] = {}
    uncomputable: list[dict[str, object]] = []
    coverage = query.coverage
    facts = query.facts

    if coverage.status != AttributionCoverageStatus.COMPLETE:
        blockers = tuple(
            _map_reason(AttributionReasonCode.BLOCKED_BY_ATTRIBUTION_FACTS),
        )
        for metric_id in _ATTRIBUTION_METRIC_IDS:
            uncomputable.append(_uncomputable(metric_id, blockers))
        return metrics, uncomputable

    direct_orders = _sum_class(facts, AttributionClass.DIRECT, orders=True)
    direct_gmv = _sum_class(facts, AttributionClass.DIRECT, orders=False)
    linked_orders = _sum_class(facts, AttributionClass.LINKED, orders=True)
    linked_gmv = _sum_class(facts, AttributionClass.LINKED, orders=False)

    if direct_orders is not None:
        metrics[ATTRIBUTION_DIRECT_ORDERS] = _metric_cell(direct_orders)
    else:
        uncomputable.append(
            _uncomputable(
                ATTRIBUTION_DIRECT_ORDERS,
                (_map_reason(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING),),
            )
        )
    if direct_gmv is not None:
        metrics[ATTRIBUTION_DIRECT_GMV_RUB] = _metric_cell(direct_gmv)
    else:
        uncomputable.append(
            _uncomputable(
                ATTRIBUTION_DIRECT_GMV_RUB,
                (_map_reason(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING),),
            )
        )
    if linked_orders is not None:
        metrics[ATTRIBUTION_LINKED_ORDERS] = _metric_cell(linked_orders)
    else:
        uncomputable.append(
            _uncomputable(
                ATTRIBUTION_LINKED_ORDERS,
                (_map_reason(AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN),),
            )
        )
    if linked_gmv is not None:
        metrics[ATTRIBUTION_LINKED_GMV_RUB] = _metric_cell(linked_gmv)
    else:
        uncomputable.append(
            _uncomputable(
                ATTRIBUTION_LINKED_GMV_RUB,
                (_map_reason(AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN),),
            )
        )

    if not can_emit_direct_linked_economics(coverage):
        _block_economics(uncomputable, _ECON_METRIC_IDS, ATTRIBUTION_BLOCKERS[0])
        return metrics, uncomputable

    spend_ok, spend_refs = assess_campaign_spend_for_economics(
        physical_adv_id=physical_adv_id,
        window_start=window_start,
        window_end=window_end,
        campaign_facts_in_window=campaign_facts_in_window,
        campaign_coverage_status=campaign_coverage_status,
    )
    if not spend_ok:
        _block_economics(uncomputable, _ECON_METRIC_IDS, CAMPAIGN_SPEND_INCOMPLETE)
        return metrics, uncomputable

    _emit_cpo_drr_pair(
        metrics,
        uncomputable,
        facts=facts,
        spend_refs=spend_refs,
        coverage=coverage,
        attr_class=AttributionClass.DIRECT,
        orders_val=direct_orders,
        gmv_val=direct_gmv,
        cpo_metric=CPO_FACT_DIRECT,
        drr_metric=DRR_FACT_DIRECT,
        missing_orders_reason=_map_reason(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING),
        missing_gmv_reason=_map_reason(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING),
    )
    _emit_cpo_drr_pair(
        metrics,
        uncomputable,
        facts=facts,
        spend_refs=spend_refs,
        coverage=coverage,
        attr_class=AttributionClass.LINKED,
        orders_val=linked_orders,
        gmv_val=linked_gmv,
        cpo_metric=CPO_FACT_LINKED,
        drr_metric=DRR_FACT_LINKED,
        missing_orders_reason=_map_reason(AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN),
        missing_gmv_reason=_map_reason(AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN),
    )

    return metrics, uncomputable


def _emit_cpo_drr_pair(
    metrics: dict[str, object],
    uncomputable: list[dict[str, object]],
    *,
    facts: tuple[AttributionCommerceFact, ...],
    spend_refs: tuple[CampaignDaySpendReference, ...],
    coverage: AttributionCoverage,
    attr_class: AttributionClass,
    orders_val: int | Decimal | None,
    gmv_val: int | Decimal | None,
    cpo_metric: str,
    drr_metric: str,
    missing_orders_reason: str,
    missing_gmv_reason: str,
) -> None:
    if orders_val is None:
        uncomputable.append(_uncomputable(cpo_metric, (missing_orders_reason,)))
    else:
        econ_cpo = compute_cpo_fact(cpo_metric, facts, spend_refs, attr_class, coverage)
        if econ_cpo.value is not None:
            metrics[cpo_metric] = _metric_cell(econ_cpo.value)
        else:
            uncomputable.append(
                _uncomputable(
                    cpo_metric, tuple(_map_reason(c) for c in econ_cpo.reason_codes)
                )
            )

    if gmv_val is None:
        uncomputable.append(_uncomputable(drr_metric, (missing_gmv_reason,)))
    else:
        econ_drr = compute_drr_fact(drr_metric, facts, spend_refs, attr_class, coverage)
        if econ_drr.value is not None:
            metrics[drr_metric] = _metric_cell(econ_drr.value)
        else:
            uncomputable.append(
                _uncomputable(
                    drr_metric, tuple(_map_reason(c) for c in econ_drr.reason_codes)
                )
            )


def package_attribution_uncomputable(included_leg_count: int) -> list[dict[str, object]]:
    """S16: package rollup не сливает Auto/Search без overlap proof."""
    if included_leg_count <= 1:
        return [
            {"metric_id": metric_id, "reason_codes": list(ATTRIBUTION_BLOCKERS)}
            for metric_id in _ATTRIBUTION_METRIC_IDS
        ]
    mismatch = (_map_reason(AttributionReasonCode.ATTRIBUTION_SCOPE_MISMATCH),)
    return [{"metric_id": metric_id, "reason_codes": list(mismatch)} for metric_id in _ATTRIBUTION_METRIC_IDS]


__all__ = [
    "ATTRIBUTION_DIRECT_GMV_RUB",
    "ATTRIBUTION_DIRECT_ORDERS",
    "ATTRIBUTION_LINKED_GMV_RUB",
    "ATTRIBUTION_LINKED_ORDERS",
    "assess_campaign_spend_for_economics",
    "build_leg_attribution_outputs",
    "package_attribution_uncomputable",
]
