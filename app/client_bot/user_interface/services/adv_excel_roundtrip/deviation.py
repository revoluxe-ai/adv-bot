"""Метрики отклонения план/факт (евклидово расстояние по % отклонений)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviationMetrics:
    orders_dev_pct: float | None
    cost_dev_pct: float | None
    deviation_score: float | None


def compute_deviation_metrics(
    *,
    fact_orders_per_day: float | None,
    plan_orders_per_day: int | None,
    fact_cost_per_order: float | None,
    target_cost_per_order: float | None,
) -> DeviationMetrics:
    """Считает относительные отклонения и sqrt(x^2+y^2).

    Если план или целевая себестоимость не заданы — компоненты и score None.
    """
    orders_dev: float | None = None
    if (
        plan_orders_per_day is not None
        and plan_orders_per_day > 0
        and fact_orders_per_day is not None
    ):
        orders_dev = (fact_orders_per_day - float(plan_orders_per_day)) / float(
            plan_orders_per_day
        )

    cost_dev: float | None = None
    if (
        target_cost_per_order is not None
        and target_cost_per_order > 0
        and fact_cost_per_order is not None
    ):
        cost_dev = (fact_cost_per_order - float(target_cost_per_order)) / float(
            target_cost_per_order
        )

    score: float | None = None
    if orders_dev is not None and cost_dev is not None:
        score = math.sqrt(orders_dev**2 + cost_dev**2)
    elif orders_dev is not None:
        score = abs(orders_dev)
    elif cost_dev is not None:
        score = abs(cost_dev)

    return DeviationMetrics(
        orders_dev_pct=orders_dev,
        cost_dev_pct=cost_dev,
        deviation_score=score,
    )
