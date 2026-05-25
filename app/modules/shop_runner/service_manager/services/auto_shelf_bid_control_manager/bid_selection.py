"""Выбор лучшей ставки по CPA между циклами control."""

from __future__ import annotations

from datetime import datetime

from .auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from .dto import BidStatsDTO


def pick_better_bid_by_cart_cpa(
    left: BidStatsDTO | None,
    right: BidStatsDTO | None,
) -> BidStatsDTO | None:
    """Минимальный ``cart_cpa``; при равенстве — меньший ``bid_minor``.

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
    left_cpa = left.cart_cpa if left.cart_cpa is not None else float("inf")
    right_cpa = right.cart_cpa if right.cart_cpa is not None else float("inf")
    if left_cpa < right_cpa:
        return left
    if right_cpa < left_cpa:
        return right
    return left if left.bid_minor <= right.bid_minor else right


async def resolve_cycle_best_bids(
    analytics: AutoShelfBidControlAnalyticsRepository,
    *,
    nmid: int,
    currency: str,
    current_cycle_started_at: datetime,
    previous_cycle_started_at: datetime | None,
) -> tuple[BidStatsDTO | None, BidStatsDTO | None, BidStatsDTO | None]:
    """Лучшие ставки текущего цикла, предыдущего и глобальная (min CPA).

    Предыдущий цикл: ``[previous_cycle_started_at, current_cycle_started_at)``,
    чтобы не дублировать данные текущего цикла.

    Returns:
        ``(cycle_best, previous_cycle_best, global_best)``.
    """
    cycle_best = await analytics.get_best_bid_by_cart_cpa(
        nmid=nmid,
        from_ts=current_cycle_started_at,
        currency=currency,
    )
    previous_cycle_best: BidStatsDTO | None = None
    if previous_cycle_started_at is not None:
        previous_cycle_best = await analytics.get_best_bid_by_cart_cpa(
            nmid=nmid,
            from_ts=previous_cycle_started_at,
            to_ts=current_cycle_started_at,
            currency=currency,
        )
    global_best = pick_better_bid_by_cart_cpa(cycle_best, previous_cycle_best)
    return cycle_best, previous_cycle_best, global_best
