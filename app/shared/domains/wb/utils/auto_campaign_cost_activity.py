"""Единое решение об активности автокампании по среднему CPO vs resolve.

При ``avg_cost > resolve`` кампания считается неактивной — watchdog ставит
автокампанию на паузу, UI показывает предупреждение.

При ``auto_shelf_bid_control_enabled`` cost-rule не применяется.
"""

from __future__ import annotations

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


def _cost_rule_controls_auto_campaign(adv_setting: AdvSetting) -> bool:
    """True, если cost-rule (пауза автокампании по среднему CPO) применяется.

    Не применяется при ``auto_shelf_bid_control_enabled``.
    """
    return not adv_setting.auto_shelf_bid_control_enabled


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
    """Build cost metrics and activity decision for an auto campaign."""
    reader = plan_fact_reader or PlanFactReader()
    plan = PlanFactProvider.get_plan_data(adv_setting)
    plan_fact_summary = await reader.get_latest_plan_fact(adv_setting.adv_id)

    cost_threshold_kind: Literal["target", "max"] | None = None
    if (
        plan is None
        or plan_fact_summary is None
        or plan_fact_summary.fact_predict_orders is None
    ):
        target_cost = None
    else:
        resolved = resolve_target_cost_and_threshold_kind(
            plan.orders,
            plan.target_pay_for_order,
            plan.max_pay_for_order,
            plan_fact_summary.fact_predict_orders,
        )
        if resolved is None:
            target_cost = None
            cost_threshold_kind = None
        else:
            target_cost, cost_threshold_kind = resolved
    avg_cost = await full_wb_adv_stat.get_additional_cost_per_order_for_adv(
        adv_setting.adv_id,
        days=days_for_avg,
    )
    ch_ts = (
        plan_fact_summary.plan_fact_ch_ts_msk
        if plan_fact_summary is not None
        else None
    )
    is_active: bool | None
    if not _cost_rule_controls_auto_campaign(adv_setting):
        is_active = True
    elif target_cost is None or avg_cost is None:
        is_active = None
    else:
        is_active = avg_cost <= target_cost

    campaign_sales_state: SalesStates | None = None
    if plan is not None:
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
        fact_pay_for_order=(
            plan_fact_summary.fact_pay_for_order
            if plan_fact_summary is not None
            else None
        ),
    )


async def is_auto_campaign_active(
    adv_setting: AdvSetting,
    *,
    plan_fact_reader: PlanFactReader | None = None,
    days_for_avg: int = 7,
) -> bool | None:
    """Return auto-campaign activity by cost rule."""
    metrics = await get_auto_campaign_cost_activity_metrics(
        adv_setting,
        plan_fact_reader=plan_fact_reader,
        days_for_avg=days_for_avg,
    )
    return metrics.is_active
