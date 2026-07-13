"""Единое решение об активности автокампании по среднему и total CPO vs resolve.

Кампания считается неактивной только при подтверждённом нарушении:
``avg_cost > resolve`` и ``fact_pay_for_order > resolve``. При нормальном
``avg_cost`` total CPO не требуется. При высоком ``avg_cost`` без плохого total
CPO результат остаётся неопределённым.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state import (
    SalesStates,
    detect_campaign_state,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    fact_data_from_plan_fact_summary,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost_and_threshold_kind,
)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


def _as_finite_cost_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    return result


def _resolve_cost_activity(
    *,
    target_cost: object,
    avg_cost: object,
    fact_pay_for_order: object,
) -> bool | None:
    """Return cost-rule activity decision using the watchdog total-CPO guard."""
    target_cost_value = _as_finite_cost_number(target_cost)
    avg_cost_value = _as_finite_cost_number(avg_cost)
    if target_cost_value is None or avg_cost_value is None:
        return None
    if avg_cost_value <= target_cost_value:
        return True

    fact_pay_for_order_value = _as_finite_cost_number(fact_pay_for_order)
    if fact_pay_for_order_value is None:
        return None
    if fact_pay_for_order_value > target_cost_value:
        return False
    return None


def _plan_fact_summary_has_finite_fact_data(plan_fact_summary: object) -> bool:
    fact_predict_orders = getattr(plan_fact_summary, "fact_predict_orders", None)
    if _as_finite_cost_number(fact_predict_orders) is None:
        return False
    fact_original_orders = getattr(plan_fact_summary, "fact_original_orders", None)
    if (
        fact_original_orders is not None
        and _as_finite_cost_number(fact_original_orders) is None
    ):
        return False
    fact_pay_for_order = getattr(plan_fact_summary, "fact_pay_for_order", None)
    return (
        fact_pay_for_order is None
        or _as_finite_cost_number(fact_pay_for_order) is not None
    )


@dataclass(frozen=True)
class AutoCampaignCostActivityMetrics:
    target_cost: float | None
    avg_cost: float | None
    is_active: bool | None
    plan_set: bool  # True if plan (orders/target/max) is present for this adv
    plan_fact_ch_ts_msk: str | None
    cost_threshold_kind: Literal["target", "max"] | None
    campaign_sales_state: SalesStates | None = None
    fact_pay_for_order: float | None = None


async def get_auto_campaign_cost_activity_metrics(
    adv_setting: AdvSetting,
    *,
    plan_fact_reader: PlanFactReader | None = None,
    days_for_avg: int = 7,
) -> AutoCampaignCostActivityMetrics:
    """Build cost metrics and the tri-state cost activity decision."""
    reader = plan_fact_reader or PlanFactReader()
    plan = PlanFactProvider.get_plan_data(adv_setting)
    plan_fact_summary = await reader.get_latest_plan_fact(adv_setting.adv_id)

    cost_threshold_kind: Literal["target", "max"] | None = None
    fact_predict_orders = (
        plan_fact_summary.fact_predict_orders
        if plan_fact_summary is not None
        else None
    )
    fact_predict_orders_value = _as_finite_cost_number(fact_predict_orders)
    if (
        plan is None
        or plan_fact_summary is None
        or fact_predict_orders_value is None
    ):
        target_cost = None
    else:
        resolved = resolve_target_cost_and_threshold_kind(
            plan.orders,
            plan.target_pay_for_order,
            plan.max_pay_for_order,
            fact_predict_orders_value,
        )
        if resolved is None:
            target_cost = None
            cost_threshold_kind = None
        else:
            target_cost, cost_threshold_kind = resolved
            target_cost = _as_finite_cost_number(target_cost)
            if target_cost is None:
                cost_threshold_kind = None
    avg_cost = await full_wb_adv_stat.get_additional_cost_per_order_for_adv(
        adv_setting.adv_id,
        days=days_for_avg,
    )
    avg_cost = _as_finite_cost_number(avg_cost)
    ch_ts = (
        plan_fact_summary.plan_fact_ch_ts_msk
        if plan_fact_summary is not None
        else None
    )
    fact_pay_for_order = (
        plan_fact_summary.fact_pay_for_order
        if plan_fact_summary is not None
        else None
    )
    fact_pay_for_order_value = _as_finite_cost_number(fact_pay_for_order)
    is_active = _resolve_cost_activity(
        target_cost=target_cost,
        avg_cost=avg_cost,
        fact_pay_for_order=fact_pay_for_order_value,
    )

    campaign_sales_state: SalesStates | None = None
    if (
        plan is not None
        and plan_fact_summary is not None
        and _plan_fact_summary_has_finite_fact_data(plan_fact_summary)
    ):
        fact = fact_data_from_plan_fact_summary(plan_fact_summary, adv_setting)
        if fact is not None:
            campaign_sales_state = detect_campaign_state(plan, fact)

    return AutoCampaignCostActivityMetrics(
        target_cost=target_cost,
        avg_cost=avg_cost,
        is_active=is_active,
        plan_set=plan is not None,
        plan_fact_ch_ts_msk=ch_ts,
        cost_threshold_kind=cost_threshold_kind,
        campaign_sales_state=campaign_sales_state,
        fact_pay_for_order=fact_pay_for_order_value,
    )


async def is_auto_campaign_active(
    adv_setting: AdvSetting,
    *,
    plan_fact_reader: PlanFactReader | None = None,
    days_for_avg: int = 7,
) -> bool | None:
    """Return the tri-state auto-campaign activity by cost rule."""
    metrics = await get_auto_campaign_cost_activity_metrics(
        adv_setting,
        plan_fact_reader=plan_fact_reader,
        days_for_avg=days_for_avg,
    )
    return metrics.is_active
