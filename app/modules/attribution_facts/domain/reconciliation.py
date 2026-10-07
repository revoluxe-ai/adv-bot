"""Сверка nm breakdown с campaign-day totals (pure domain, без БД)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.attribution_facts.domain.enums import AttributionReasonCode
from app.modules.attribution_facts.domain.models import (
    CampaignDayTotals,
    DayReconciliationResult,
    NmDayContribution,
)

DEFAULT_GMV_EPSILON_RUB = Decimal("0.01")


def reconcile_campaign_day(
    day: CampaignDayTotals,
    nm_rows: tuple[NmDayContribution, ...],
    *,
    gmv_epsilon: Decimal = DEFAULT_GMV_EPSILON_RUB,
) -> DayReconciliationResult:
    """
    Сверить суммы nm/app с дневными totals того же adv.

    Args:
        day: Авторитетные дневные orders/GMV.
        nm_rows: Разбивка по ordered_nm_id и app_type.
        gmv_epsilon: Допуск для sum_price.

    Returns:
        Результат с unattributed_orders при расхождении.
    """
    nm_orders = sum(row.orders for row in nm_rows)
    nm_gmv = sum((row.gmv_rub for row in nm_rows), start=Decimal("0"))
    orders_match = nm_orders == day.orders
    gmv_match = abs(nm_gmv - day.gmv_rub) <= gmv_epsilon
    passed = orders_match and gmv_match
    unattributed = max(day.orders - nm_orders, 0) if not orders_match else 0
    reason_codes: tuple[AttributionReasonCode, ...] = ()
    if not passed:
        reason_codes = (AttributionReasonCode.RECONCILIATION_FAILED,)
    return DayReconciliationResult(
        physical_adv_id=day.physical_adv_id,
        event_date=day.event_date,
        passed=passed,
        nm_orders_sum=nm_orders,
        day_orders=day.orders,
        nm_gmv_sum=nm_gmv,
        day_gmv_rub=day.gmv_rub,
        unattributed_orders=unattributed,
        reason_codes=reason_codes,
    )
