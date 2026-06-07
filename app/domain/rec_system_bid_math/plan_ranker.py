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
    *,
    cost_penalty_alpha: float = 1.0,
) -> list[dict[str, Any]]:
    """Ранжировать все ставки по близости к плану и стоимости заказа.

    Исходные строки из ``expected_ranked`` не изменяются. Для каждой ставки
    возвращается новая строка с расчётами кликов, заказов, стоимости и итогового
    plan score. Меньший score означает более подходящую ставку.
    """
    resolved_order_cost = (
        context.max_order_cost
        if context.current_sales_forecast < context.sales_plan
        else context.target_order_cost
    )
    ranked_rows: list[dict[str, Any]] = []

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
        sales_gap = abs(projected_sales - context.sales_plan)
        order_cost_overlimit = max(0.0, expected_order_cost - resolved_order_cost)
        plan_score = sales_gap + cost_penalty_alpha * order_cost_overlimit

        ranked_rows.append(
            {
                "bid": bid,
                "ctr": ctr,
                "expected_impressions": expected_impressions,
                "expected_clicks": expected_clicks,
                "expected_orders": expected_orders,
                "expected_cost": expected_cost,
                "expected_order_cost": expected_order_cost,
                "resolved_order_cost": resolved_order_cost,
                "projected_sales": projected_sales,
                "sales_gap": sales_gap,
                "order_cost_overlimit": order_cost_overlimit,
                "plan_score": plan_score,
                "confidence": row["confidence"],
                "uncertainty": row["uncertainty"],
                "main_score": row["main_score"],
                "test_score": row["test_score"],
                "own_anchor": row["own_anchor"],
            }
        )

    return sorted(ranked_rows, key=lambda row: row["plan_score"])
