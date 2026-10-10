"""
V1 campaign economics только из DIRECT attribution facts.

LINKED не входит в GMV, orders, DRR и target CPO. Supplier-order строки
здесь не используются.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.runtime.money import quantize_percent, quantize_rub
from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionCoverage,
    DateWindow,
)


@dataclass(frozen=True, slots=True)
class CampaignOrderValue:
    """Диагностический target CPO и фактический DRR кампании."""

    direct_gmv_rub: Decimal | None
    direct_orders: int | None
    expected_order_value_rub: Decimal | None
    target_cpo_rub: Decimal | None
    campaign_actual_drr_percent: Decimal | None
    reason_codes: tuple[AdControlReasonCode, ...]


def campaign_order_value(
    facts: tuple[AttributionCommerceFact, ...],
    coverage: AttributionCoverage,
    *,
    campaign_spend_rub: Decimal | None,
    effective_target_drr_percent: Decimal | None,
    window: DateWindow,
    facts_stale: bool = False,
) -> CampaignOrderValue:
    """
    Посчитать EOV и target CPO из сумм DIRECT, не из среднего по nm.

    Args:
        facts: факты scope кампании, включая LINKED (они игнорируются).
        coverage: покрытие того же окна.
        campaign_spend_rub: spend кампании за то же окно; None — нет числителя.
        effective_target_drr_percent: эффективный target DRR в процентах.
        window: окно spend/GMV; лаг ``source_complete_through`` сверяется с ним.
        facts_stale: явная метка stale поверх coverage.
    """
    direct = tuple(
        fact for fact in facts if fact.attribution_class == AttributionClass.DIRECT
    )
    if coverage.status != AttributionCoverageStatus.COMPLETE:
        if not direct and coverage.status == AttributionCoverageStatus.NO_DATA:
            return _blocked(AdControlReasonCode.DIRECT_ATTRIBUTION_MISSING)
        return _blocked(AdControlReasonCode.ATTRIBUTION_WINDOW_INCOMPLETE)
    if not direct:
        return _blocked(AdControlReasonCode.DIRECT_ATTRIBUTION_MISSING)
    lagged = (
        coverage.source_complete_through is not None
        and coverage.source_complete_through < window.end
    )
    if facts_stale or lagged:
        return _blocked(AdControlReasonCode.ATTRIBUTION_FACT_STALE)
    orders = _sum_orders(direct)
    gmv = _sum_gmv(direct)
    if orders is None or gmv is None:
        return _blocked(AdControlReasonCode.DIRECT_ATTRIBUTION_INSUFFICIENT)
    if orders == 0:
        return _blocked(AdControlReasonCode.ORDER_VALUE_UNAVAILABLE)
    if campaign_spend_rub is None or effective_target_drr_percent is None:
        return _blocked(AdControlReasonCode.CPO_INPUTS_INCOMPLETE)
    expected = gmv / Decimal(orders)
    target = quantize_rub(expected * effective_target_drr_percent / Decimal(100))
    actual_percent: Decimal | None
    if gmv == 0:
        actual_percent = None
    else:
        actual_percent = quantize_percent(campaign_spend_rub / gmv * Decimal(100))
    return CampaignOrderValue(
        direct_gmv_rub=gmv,
        direct_orders=orders,
        expected_order_value_rub=expected,
        target_cpo_rub=target,
        campaign_actual_drr_percent=actual_percent,
        reason_codes=(),
    )


def _sum_orders(facts: tuple[AttributionCommerceFact, ...]) -> int | None:
    total = 0
    for fact in facts:
        if fact.metrics.attributed_orders is None:
            return None
        total += fact.metrics.attributed_orders
    return total


def _sum_gmv(facts: tuple[AttributionCommerceFact, ...]) -> Decimal | None:
    total = Decimal(0)
    for fact in facts:
        if fact.metrics.attributed_gmv_rub is None:
            return None
        total += fact.metrics.attributed_gmv_rub
    return total


def _blocked(reason: AdControlReasonCode) -> CampaignOrderValue:
    return CampaignOrderValue(
        direct_gmv_rub=None,
        direct_orders=None,
        expected_order_value_rub=None,
        target_cpo_rub=None,
        campaign_actual_drr_percent=None,
        reason_codes=(reason,),
    )
