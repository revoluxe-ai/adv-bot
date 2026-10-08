"""Attribution facts → analysis metrics (domain formulas, fail-closed)."""

from __future__ import annotations

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
    AttributionQueryResult,
    CampaignDaySpendReference,
)
from app.modules.ai_package_v1.analysis.constants import (
    ATTRIBUTION_BLOCKERS,
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

_ATTRIBUTION_METRIC_IDS: tuple[str, ...] = (
    ATTRIBUTION_DIRECT_ORDERS,
    ATTRIBUTION_DIRECT_GMV_RUB,
    ATTRIBUTION_LINKED_ORDERS,
    ATTRIBUTION_LINKED_GMV_RUB,
    CPO_FACT_DIRECT,
    CPO_FACT_LINKED,
    DRR_FACT_DIRECT,
    DRR_FACT_LINKED,
)


def spend_refs_for_leg_window(
    facts: list[CampaignDailyFact],
) -> tuple[CampaignDaySpendReference, ...]:
    """Один spend на physical_adv_id × event_date (authority full_adv_wb_stat)."""
    refs: list[CampaignDaySpendReference] = []
    for fact in facts:
        if fact.spend_rub is None:
            continue
        refs.append(
            CampaignDaySpendReference(
                physical_adv_id=fact.adv_id,
                event_date=fact.stat_date,
                spend_rub=Decimal(str(fact.spend_rub)),
            )
        )
    return tuple(refs)


def _sum_class(
    facts: tuple[AttributionCommerceFact, ...],
    attr_class: AttributionClass,
    *,
    orders: bool,
) -> int | Decimal | None:
    total_orders = 0
    total_gmv = Decimal(0)
    saw_orders = False
    saw_gmv = False
    for fact in facts:
        if fact.attribution_class != attr_class:
            continue
        if orders:
            if fact.metrics.attributed_orders is None:
                return None
            total_orders += fact.metrics.attributed_orders
            saw_orders = True
        else:
            if fact.metrics.attributed_gmv_rub is None:
                return None
            total_gmv += fact.metrics.attributed_gmv_rub
            saw_gmv = True
    if orders:
        return total_orders if saw_orders else None
    return total_gmv if saw_gmv else None


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


def build_leg_attribution_outputs(
    query: AttributionQueryResult,
    spend_refs: tuple[CampaignDaySpendReference, ...],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """
    Сформировать metrics/uncomputable для одной ноги × окно.

    Numeric economics только при COMPLETE coverage и PASS reconciliation grid.
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
        for metric_id in (CPO_FACT_DIRECT, DRR_FACT_DIRECT, CPO_FACT_LINKED, DRR_FACT_LINKED):
            uncomputable.append(_uncomputable(metric_id, tuple(ATTRIBUTION_BLOCKERS)))
        return metrics, uncomputable

    if direct_orders is None:
        for metric_id in (CPO_FACT_DIRECT, DRR_FACT_DIRECT):
            uncomputable.append(
                _uncomputable(
                    metric_id,
                    (_map_reason(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING),),
                )
            )
    else:
        for metric_name, attr_class, compute in (
            (CPO_FACT_DIRECT, AttributionClass.DIRECT, compute_cpo_fact),
        ):
            econ = compute(metric_name, facts, spend_refs, attr_class, coverage)
            if econ.value is not None:
                metrics[metric_name] = _metric_cell(econ.value)
            else:
                uncomputable.append(
                    _uncomputable(
                        metric_name, tuple(_map_reason(c) for c in econ.reason_codes)
                    )
                )
        econ_drr = compute_drr_fact(
            DRR_FACT_DIRECT, facts, spend_refs, AttributionClass.DIRECT, coverage
        )
        if econ_drr.value is not None:
            metrics[DRR_FACT_DIRECT] = _metric_cell(econ_drr.value)
        else:
            uncomputable.append(
                _uncomputable(
                    DRR_FACT_DIRECT, tuple(_map_reason(c) for c in econ_drr.reason_codes)
                )
            )

    if linked_orders is None:
        for metric_id in (CPO_FACT_LINKED, DRR_FACT_LINKED):
            uncomputable.append(
                _uncomputable(
                    metric_id,
                    (_map_reason(AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN),),
                )
            )
    else:
        econ_cpo = compute_cpo_fact(
            CPO_FACT_LINKED, facts, spend_refs, AttributionClass.LINKED, coverage
        )
        if econ_cpo.value is not None:
            metrics[CPO_FACT_LINKED] = _metric_cell(econ_cpo.value)
        else:
            uncomputable.append(
                _uncomputable(
                    CPO_FACT_LINKED, tuple(_map_reason(c) for c in econ_cpo.reason_codes)
                )
            )
        econ_drr_l = compute_drr_fact(
            DRR_FACT_LINKED, facts, spend_refs, AttributionClass.LINKED, coverage
        )
        if econ_drr_l.value is not None:
            metrics[DRR_FACT_LINKED] = _metric_cell(econ_drr_l.value)
        else:
            uncomputable.append(
                _uncomputable(
                    DRR_FACT_LINKED, tuple(_map_reason(c) for c in econ_drr_l.reason_codes)
                )
            )

    return metrics, uncomputable


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
    "build_leg_attribution_outputs",
    "package_attribution_uncomputable",
    "spend_refs_for_leg_window",
]
