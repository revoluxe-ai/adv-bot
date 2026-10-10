"""Производные CPO/DRR (fail-closed, без дублирования spend authority)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.attribution_facts.domain.coverage import (
    can_emit_direct_linked_economics,
)
from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionReasonCode,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionCoverage,
    CampaignDaySpendReference,
    DerivedFactEconomics,
)


def _sum_metric(
    facts: tuple[AttributionCommerceFact, ...],
    attr_class: AttributionClass,
    *,
    orders: bool,
) -> int | Decimal | None:
    """
    Сумма метрики класса; None если любой вклад класса без значения (missing ≠ 0).
    """
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


def _sum_spend(spend_refs: tuple[CampaignDaySpendReference, ...]) -> Decimal | None:
    if not spend_refs:
        return None
    return sum((ref.spend_rub for ref in spend_refs), start=Decimal(0))


def compute_cpo_fact(
    metric_name: str,
    facts: tuple[AttributionCommerceFact, ...],
    spend_refs: tuple[CampaignDaySpendReference, ...],
    attr_class: AttributionClass,
    coverage: AttributionCoverage,
) -> DerivedFactEconomics:
    """
    CPO_FACT_* = spend / attributed orders для класса.

    Returns:
        value None + reason codes (missing denominator ≠ DENOMINATOR_ZERO).
    """
    if not can_emit_direct_linked_economics(coverage):
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.BLOCKED_BY_ATTRIBUTION_FACTS,),
        )
    orders = _sum_metric(facts, attr_class, orders=True)
    if orders is None:
        missing = (
            AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN
            if attr_class == AttributionClass.LINKED
            else AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING
        )
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(missing,),
        )
    if orders == 0:
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.DENOMINATOR_ZERO,),
        )
    spend = _sum_spend(spend_refs)
    if spend is None:
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING,),
        )
    return DerivedFactEconomics(
        metric_name=metric_name,
        value=spend / Decimal(orders),
        reason_codes=(),
    )


def compute_drr_fact(
    metric_name: str,
    facts: tuple[AttributionCommerceFact, ...],
    spend_refs: tuple[CampaignDaySpendReference, ...],
    attr_class: AttributionClass,
    coverage: AttributionCoverage,
) -> DerivedFactEconomics:
    """DRR_FACT_* = spend / attributed GMV для класса."""
    if not can_emit_direct_linked_economics(coverage):
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.BLOCKED_BY_ATTRIBUTION_FACTS,),
        )
    gmv = _sum_metric(facts, attr_class, orders=False)
    if gmv is None:
        missing = (
            AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN
            if attr_class == AttributionClass.LINKED
            else AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING
        )
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(missing,),
        )
    if gmv == 0:
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.DENOMINATOR_ZERO,),
        )
    spend = _sum_spend(spend_refs)
    if spend is None:
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING,),
        )
    return DerivedFactEconomics(
        metric_name=metric_name,
        value=spend / gmv,
        reason_codes=(),
    )
