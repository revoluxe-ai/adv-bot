"""Выбор лучшей ставки по CPC или CTR между циклами control.

Сравнение кандидатов:
- CPC mode: по ``BidStatsDTO.cart_cpa`` (фактически CPC score)
- CTR mode: по ``BidStatsDTO.ctr`` (click-through rate)

Имя поля cart_cpa временное, см. dto/bid_stats_dto.py.
"""

from __future__ import annotations

from datetime import datetime

from .auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from .dto import BidStatsDTO, OptimizationMetric


def pick_better_bid_by_cart_cpa(
    left: BidStatsDTO | None,
    right: BidStatsDTO | None,
) -> BidStatsDTO | None:
    """Минимальный CPC (поле ``cart_cpa``); при равенстве — меньший ``bid_minor``.

    Args:
        left: Кандидат слева (например текущий цикл).
        right: Кандидат справа (например предыдущий цикл).

    Returns:
        Лучший кандидат или ``None``, если оба пустые.
    """
    if left is None:
        return right
    if right is None:
        return left
    left_cpc = left.cart_cpa if left.cart_cpa is not None else float("inf")
    right_cpc = right.cart_cpa if right.cart_cpa is not None else float("inf")
    if left_cpc < right_cpc:
        return left
    if right_cpc < left_cpc:
        return right
    return left if left.bid_minor <= right.bid_minor else right


def pick_better_bid_by_ctr(
    left: BidStatsDTO | None,
    right: BidStatsDTO | None,
) -> BidStatsDTO | None:
    """Максимальный CTR; при равенстве — меньший ``bid_minor``.

    Args:
        left: Кандидат слева (например текущий цикл).
        right: Кандидат справа (например предыдущий цикл).

    Returns:
        Лучший кандидат или ``None``, если оба пустые.
    """
    if left is None:
        return right
    if right is None:
        return left
    left_ctr = left.ctr if left.ctr is not None else float("-inf")
    right_ctr = right.ctr if right.ctr is not None else float("-inf")
    if left_ctr > right_ctr:
        return left
    if right_ctr > left_ctr:
        return right
    return left if left.bid_minor <= right.bid_minor else right


async def resolve_cycle_best_bids(
    analytics: AutoShelfBidControlAnalyticsRepository,
    *,
    nmid: int,
    currency: str,
    current_cycle_started_at: datetime,
    previous_cycle_started_at: datetime | None,
    fact_cpo: float | None = None,
    resolve_cpo: float | None = None,
) -> tuple[BidStatsDTO | None, BidStatsDTO | None, BidStatsDTO | None]:
    """Лучшие ставки текущего цикла, предыдущего и глобальная.

    Метрика оптимизации выбирается на основе CPO:
    - CTR: когда fact_cpo < resolve_cpo (оптимизируем клики)
    - CPC: когда fact_cpo >= resolve_cpo (оптимизируем стоимость)

    Предыдущий цикл: ``[previous_cycle_started_at, current_cycle_started_at)``,
    чтобы не дублировать данные текущего цикла.
    Кандидаты — любые точки с ``impressions > 0`` (и ``clicks > 0`` для CPC).

    Args:
        analytics: Репозиторий для чтения аналитики
        nmid: Номенклатурный номер
        currency: Валюта
        current_cycle_started_at: Начало текущего цикла
        previous_cycle_started_at: Начало предыдущего цикла (None если первый)
        fact_cpo: Фактическое CPO кампании
        resolve_cpo: Resolve/target CPO кампании

    Returns:
        ``(cycle_best, previous_cycle_best, global_best)``.
    """
    from .dto import resolve_optimization_metric as _resolve_metric

    metric = _resolve_metric(fact_cpo, resolve_cpo)

    if metric == OptimizationMetric.CTR:
        cycle_best = await analytics.get_best_bid_by_ctr(
            nmid=nmid,
            from_ts=current_cycle_started_at,
            currency=currency,
        )
        previous_cycle_best: BidStatsDTO | None = None
        if previous_cycle_started_at is not None:
            previous_cycle_best = await analytics.get_best_bid_by_ctr(
                nmid=nmid,
                from_ts=previous_cycle_started_at,
                to_ts=current_cycle_started_at,
                currency=currency,
            )
        global_best = pick_better_bid_by_ctr(cycle_best, previous_cycle_best)
    else:
        cycle_best = await analytics.get_best_bid_by_cart_cpa(
            nmid=nmid,
            from_ts=current_cycle_started_at,
            currency=currency,
        )
        previous_cycle_best = None
        if previous_cycle_started_at is not None:
            previous_cycle_best = await analytics.get_best_bid_by_cart_cpa(
                nmid=nmid,
                from_ts=previous_cycle_started_at,
                to_ts=current_cycle_started_at,
                currency=currency,
            )
        global_best = pick_better_bid_by_cart_cpa(cycle_best, previous_cycle_best)

    return cycle_best, previous_cycle_best, global_best
