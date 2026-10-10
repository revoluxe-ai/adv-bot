"""Projection local policy state from AdvSetting (read-only)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.models.snapshot import LocalPolicyStateV1


def project_local_policy_from_adv_setting(row: AdvSetting) -> LocalPolicyStateV1:
    """Extract bounded policy subsets for planning/state_token."""
    budget = {
        "auto_budget_watchdog_enabled": row.auto_budget_watchdog_enabled,
        "auto_budget_daily_limit": row.auto_budget_daily_limit,
        "search_auto_budget_daily_limit": row.search_auto_budget_daily_limit,
        "use_common_budget": row.use_common_budget,
        "common_budget_daily_limit": row.common_budget_daily_limit,
        "auto_budget_total_limit": row.auto_budget_total_limit,
        "search_auto_budget_total_limit": row.search_auto_budget_total_limit,
        "common_budget_total_limit": row.common_budget_total_limit,
    }
    sales: dict[str, object] = {
        "orders_source_for_auto_mode": row.orders_source_for_auto_mode.value,
        "plan_for_sales_for_day": row.plan_for_sales_for_day,
        "target_price_for_order": row.target_price_for_order,
        "max_price_for_order": row.max_price_for_order,
        "sales_predict_method": row.sales_predict_method.value,
        "strategy": row.strategy.value if row.strategy is not None else None,
        "auto_update_strategy": row.auto_update_strategy,
    }
    bid_control: dict[str, object] = {
        "auto_shelf_bid_control_enabled": row.auto_shelf_bid_control_enabled,
        "auto_shelf_bid_control_strategy": (
            row.auto_shelf_bid_control_strategy.value
            if row.auto_shelf_bid_control_strategy is not None
            else None
        ),
    }
    budget_out: dict[str, object] = dict(budget)
    return LocalPolicyStateV1(budget=budget_out, sales=sales, bid_control=bid_control)
