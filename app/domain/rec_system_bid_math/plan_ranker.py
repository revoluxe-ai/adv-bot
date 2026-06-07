"""Ранжирование результатов bid-модели относительно плана продаж."""

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanContext:
    """Контекст плана продаж и допустимой стоимости заказа."""

    sales_plan: float
    current_fact_sales: float
    current_sales_forecast: float
    target_order_cost: float
    max_order_cost: float
    click_to_order_cr_7d: float


def rank_bids_for_sales_plan(
    bid_model_result: dict[str, Any],
    context: PlanContext,
    ctr_by_bid: dict[int, float],
) -> list[dict[str, Any]]:
    """Ранжировать все ставки по нормализованному одностороннему расстоянию.

    Чем меньше plan_score, тем ближе ставка к целевой зоне:
    недобор продаж штрафуется только снизу, а перерасход CPO только сверху.
    """
    ranked_rows: list[dict[str, Any]] = []
    needed_sales = max(1.0, context.sales_plan - context.current_fact_sales)
    target_order_cost_minor = context.target_order_cost * 100.0
    max_order_cost_minor = context.max_order_cost * 100.0

    for row in bid_model_result["expected_ranked"]:
        bid = int(row["bid"])
        ctr = ctr_by_bid[bid]
        expected_impressions = float(row["expected_daily_impressions"])
        expected_clicks = expected_impressions * ctr
        expected_orders = expected_clicks * context.click_to_order_cr_7d
        expected_cost = expected_impressions / 1000.0 * bid
        if expected_orders > 0:
            expected_order_cost = expected_cost / expected_orders
        else:
            expected_order_cost = math.inf
        projected_sales = context.current_fact_sales + expected_orders
        if projected_sales < context.sales_plan:
            resolved_order_cost = max_order_cost_minor
        else:
            resolved_order_cost = target_order_cost_minor
        sales_miss = max(0.0, context.sales_plan - projected_sales)
        cpo_over = max(0.0, expected_order_cost - resolved_order_cost)
        sales_dist = sales_miss / needed_sales
        cpo_dist = cpo_over / resolved_order_cost if resolved_order_cost > 0 else math.inf
        plan_score = math.sqrt(sales_dist**2 + cpo_dist**2)

        ranked_rows.append(
            {
                "bid": bid,
                "ctr": ctr,
                "expected_impressions": expected_impressions,
                "expected_clicks": expected_clicks,
                "expected_orders": expected_orders,
                "expected_cost": expected_cost,
                "expected_order_cost_minor": expected_order_cost,
                "expected_order_cost_rub": expected_order_cost / 100.0,
                "resolved_order_cost_minor": resolved_order_cost,
                "resolved_order_cost_rub": resolved_order_cost / 100.0,
                "projected_sales": projected_sales,
                "needed_sales": needed_sales,
                "sales_miss": sales_miss,
                "sales_dist": sales_dist,
                "cpo_over_minor": cpo_over,
                "cpo_over_rub": cpo_over / 100.0,
                "cpo_dist": cpo_dist,
                "plan_score": plan_score,
                "confidence": row["confidence"],
                "uncertainty": row["uncertainty"],
                "main_score": row["main_score"],
                "test_score": row["test_score"],
                "own_anchor": row["own_anchor"],
            }
        )

    return sorted(ranked_rows, key=lambda row: row["plan_score"])
