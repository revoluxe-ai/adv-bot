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
    if day.orders is None or day.gmv_rub is None:
        return DayReconciliationResult(
            physical_adv_id=day.physical_adv_id,
            event_date=day.event_date,
            passed=False,
            nm_orders_sum=0,
            day_orders=day.orders or 0,
            nm_gmv_sum=Decimal(0),
            day_gmv_rub=day.gmv_rub or Decimal(0),
            unattributed_orders=0,
            reason_codes=(AttributionReasonCode.RECONCILIATION_FAILED,),
        )
    if any(row.orders is None or row.gmv_rub is None for row in nm_rows):
        return DayReconciliationResult(
            physical_adv_id=day.physical_adv_id,
            event_date=day.event_date,
            passed=False,
            nm_orders_sum=0,
            day_orders=day.orders,
            nm_gmv_sum=Decimal(0),
            day_gmv_rub=day.gmv_rub,
            unattributed_orders=day.orders,
            reason_codes=(AttributionReasonCode.RECONCILIATION_FAILED,),
        )
    nm_orders = 0
    nm_gmv = Decimal(0)
    for row in nm_rows:
        order_val = row.orders
        gmv_val = row.gmv_rub
        assert order_val is not None and gmv_val is not None
        nm_orders += order_val
        nm_gmv += gmv_val
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
