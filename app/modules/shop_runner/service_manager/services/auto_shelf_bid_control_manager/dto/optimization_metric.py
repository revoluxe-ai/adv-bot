"""Метрика оптимизации для выбора лучшей ставки."""

from __future__ import annotations

from enum import StrEnum


class OptimizationMetric(StrEnum):
    """Метрика оптимизации для выбора лучшей ставки."""

    CPC = "cpc"  # Минимальный cost per click (spend / clicks)
    CTR = "ctr"  # Максимальный click-through rate (clicks / impressions)


def resolve_optimization_metric(
    fact_cpo: float | None,
    resolve_cpo: float | None,
) -> OptimizationMetric:
    """Определить метрику оптимизации на основе CPO кампании.

    - CTR: когда фактическое CPO < resolve CPO (оптимизируем клики)
    - CPC: когда фактическое CPO >= resolve CPO (оптимизируем стоимость)

    Args:
        fact_cpo: Фактическое CPO из plan-fact статистики
        resolve_cpo: Resolve/target CPO кампании

    Returns:
        OptimizationMetric.CTR или OptimizationMetric.CPC
    """
    if fact_cpo is not None and resolve_cpo is not None and fact_cpo < resolve_cpo:
        return OptimizationMetric.CTR
    return OptimizationMetric.CPC
