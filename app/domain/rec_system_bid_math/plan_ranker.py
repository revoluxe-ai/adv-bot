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

    def __post_init__(self) -> None:
        """Валидирует шкалу CR: ожидается доля, а не проценты."""
        if not 0.0 <= self.click_to_order_cr_7d <= 1.0:
            raise ValueError(
                "click_to_order_cr_7d must be a fraction in [0, 1], "
                f"got {self.click_to_order_cr_7d!r}"
            )


def rank_bids_for_sales_plan(
    bid_model_result: dict[str, Any],
    context: PlanContext,
    ctr_by_bid: dict[int, float],
) -> list[dict[str, Any]]:
    """Ранжировать все ставки по нормализованному расстоянию до целевой зоны.

    Чем меньше ``plan_distance_score``, тем ближе ставка к целевой зоне:
    недобор продаж штрафуется только снизу, а перерасход стоимости заказа только сверху.
    Обе компоненты нормализованы до безразмерной шкалы.
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
        expected_cost_minor = expected_impressions / 1000.0 * bid
        if expected_orders > 0:
            expected_order_cost_minor = expected_cost_minor / expected_orders
        else:
            expected_order_cost_minor = math.inf
        projected_sales = context.current_fact_sales + expected_orders
        sales_gap = projected_sales - context.sales_plan
        abs_sales_gap = abs(sales_gap)
        if projected_sales < context.sales_plan:
            resolved_order_cost_minor = max_order_cost_minor
        else:
            resolved_order_cost_minor = target_order_cost_minor
        sales_miss = max(0.0, context.sales_plan - projected_sales)
        order_cost_overlimit_minor = max(
            0.0, expected_order_cost_minor - resolved_order_cost_minor
        )
        sales_dist = sales_miss / needed_sales
        order_cost_overlimit_dist = (
            order_cost_overlimit_minor / resolved_order_cost_minor
            if resolved_order_cost_minor > 0
            else math.inf
        )
        plan_distance_score = math.sqrt(
            sales_dist**2 + order_cost_overlimit_dist**2
        )

        ranked_rows.append(
            {
                "bid": bid,
                "ctr": ctr,
                "expected_impressions": expected_impressions,
                "expected_clicks": expected_clicks,
                "expected_orders": expected_orders,
                "expected_cost_minor": expected_cost_minor,
                "expected_cost_rub": expected_cost_minor / 100.0,
                "expected_order_cost_minor": expected_order_cost_minor,
                "expected_order_cost_rub": expected_order_cost_minor / 100.0,
                "resolved_order_cost_minor": resolved_order_cost_minor,
                "resolved_order_cost_rub": resolved_order_cost_minor / 100.0,
                "projected_sales": projected_sales,
                "sales_gap": sales_gap,
                "abs_sales_gap": abs_sales_gap,
                "needed_sales": needed_sales,
                "sales_miss": sales_miss,
                "sales_dist": sales_dist,
                "order_cost_overlimit_minor": order_cost_overlimit_minor,
                "order_cost_overlimit_rub": order_cost_overlimit_minor / 100.0,
                "order_cost_overlimit_dist": order_cost_overlimit_dist,
                "plan_distance_score": plan_distance_score,
                "confidence": row["confidence"],
                "uncertainty": row["uncertainty"],
                "main_score": row["main_score"],
                "test_score": row["test_score"],
                "own_anchor": row["own_anchor"],
            }
        )

    return sorted(ranked_rows, key=lambda row: row["plan_distance_score"])
