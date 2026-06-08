"""Shared builders for rec-bid recommendation plan context."""

from __future__ import annotations

from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost


def build_rec_bid_plan_context(
    *,
    sales_plan: float,
    current_fact_sales: float,
    current_sales_forecast: float,
    target_price_for_order: float | None,
    max_price_for_order: float | None,
    click_to_order_cr_7d: float,
) -> PlanContext:
    """Build PlanContext with the same target-cost semantics as control."""
    resolved_target_cost = resolve_target_cost(
        sales_plan,
        target_price_for_order,
        max_price_for_order,
        current_sales_forecast,
    )
    if resolved_target_cost is None:
        resolved_target_cost = float(max_price_for_order or 0.0)
    return PlanContext(
        sales_plan=float(sales_plan or 0.0),
        current_fact_sales=float(current_fact_sales or 0.0),
        current_sales_forecast=float(current_sales_forecast or 0.0),
        target_order_cost=resolved_target_cost,
        max_order_cost=float(max_price_for_order or 0.0),
        click_to_order_cr_7d=float(click_to_order_cr_7d or 0.0),
    )
