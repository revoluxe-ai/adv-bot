"""Метрики отклонения план/факт (евклидово расстояние по % отклонений)."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Относительное отклонение (fact-plan)/plan в долях -> процентные пункты для UI/Excel
_PCT = 100.0


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
    """Считает относительные отклонения в процентах (п.п.) и sqrt(x^2+y^2) в той же шкале.

    Например, при факте на 50% ниже плана по заказам: orders_dev_pct == -50.0.

    Если план или целевая себестоимость не заданы — компоненты и score None.
    """
    orders_ratio: float | None = None
    if (
        plan_orders_per_day is not None
        and plan_orders_per_day > 0
        and fact_orders_per_day is not None
    ):
        orders_ratio = (fact_orders_per_day - float(plan_orders_per_day)) / float(
            plan_orders_per_day
        )

    cost_ratio: float | None = None
    if (
        target_cost_per_order is not None
        and target_cost_per_order > 0
        and fact_cost_per_order is not None
    ):
        cost_ratio = (fact_cost_per_order - float(target_cost_per_order)) / float(
            target_cost_per_order
        )

    orders_dev = orders_ratio * _PCT if orders_ratio is not None else None
    cost_dev = cost_ratio * _PCT if cost_ratio is not None else None

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
