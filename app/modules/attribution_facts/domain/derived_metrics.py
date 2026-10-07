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
) -> int | Decimal:
    total_orders = 0
    total_gmv = Decimal(0)
    for fact in facts:
        if fact.attribution_class != attr_class:
            continue
        if orders:
            if fact.metrics.attributed_orders is not None:
                total_orders += fact.metrics.attributed_orders
        elif fact.metrics.attributed_gmv_rub is not None:
            total_gmv += fact.metrics.attributed_gmv_rub
    return total_orders if orders else total_gmv


def _sum_spend(spend_refs: tuple[CampaignDaySpendReference, ...]) -> Decimal:
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
        value None + DENOMINATOR_ZERO или BLOCKED при fail-closed.
    """
    if not can_emit_direct_linked_economics(coverage):
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.BLOCKED_BY_ATTRIBUTION_FACTS,),
        )
    orders = _sum_metric(facts, attr_class, orders=True)
    if orders <= 0:
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.DENOMINATOR_ZERO,),
        )
    spend = _sum_spend(spend_refs)
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
    """
    DRR_FACT_* = spend / attributed GMV для класса.
    """
    if not can_emit_direct_linked_economics(coverage):
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.BLOCKED_BY_ATTRIBUTION_FACTS,),
        )
    gmv = _sum_metric(facts, attr_class, orders=False)
    if not isinstance(gmv, Decimal) or gmv <= 0:
        return DerivedFactEconomics(
            metric_name=metric_name,
            value=None,
            reason_codes=(AttributionReasonCode.DENOMINATOR_ZERO,),
        )
    spend = _sum_spend(spend_refs)
    return DerivedFactEconomics(
        metric_name=metric_name,
        value=spend / gmv,
        reason_codes=(),
    )
