"""Нормализованный баланс conv/CPO для выбора OPTIMUM (V3).

SSOT для ``candidates.build_mode_candidates`` и
``PredictKeywordsTargetPlace.get_target_position_for_strategy_mode``.
Без импорта ``auto_updater_v3`` (избегаем цикла с predict).

Production OPTIMUM (``select_optimum_row_production``):

- Balance на всём usable-профиле: max ``0.5*conv_n + 0.5*economy_n`` (без CPO-cap).
- OPTIMUM может совпадать с MIN_CPA или MAX_CONVERSION — честный результат данных.
- Ограничение дорогой агрессии — resolve, MAX_CPA_GUARD, trim, не формула OPT.

Compare/debug (не production):

- **A** / **B**: альтернативные веса/center_bonus (``select_optimum_row``).
- **C** (``select_optimum_row_cpo_cap``): cap 1.3 / 1.5 / 2.0 — тесты, compare-скрипты.

Нормализация balance (внутри выбранного пула):

- ``conv_n = (conv - conv_min) / (conv_max - conv_min)`` (вырождение → 1).
- ``cpa_n = (cpo - cpo_min) / (cpo_max - cpo_min)`` (вырождение → 1).
- ``economy_n = 1 - cpa_n``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Literal, Protocol, TypeVar, cast

from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)

OPTIMUM_CONV_WEIGHT = 0.5
OPTIMUM_ECONOMY_WEIGHT = 0.5
OPTIMUM_SCORE_EPS = 1e-6
OPTIMUM_MAX_CPO_PENALTY_COMPARE = 1.5

# Вариант A (compare/debug)
VARIANT_A_BALANCE_WEIGHT = 0.8
VARIANT_A_CENTER_WEIGHT = 0.2
VARIANT_B_CENTER_WEIGHT = 0.2


class OptimumScoreMode(str, Enum):
    """Режим расчёта optimum_score для compare/debug (не production)."""

    CURRENT = "current"
    VARIANT_A = "A"
    VARIANT_B = "B"


class _HasPositionBid(Protocol):
    position: int
    bid: int | float


# Без bound: mypy не считает Pydantic/dataclass структурно совместимыми с Protocol.
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class NormalizedPointMetrics:
    """Нормализованные метрики одной точки CH-профиля."""

    conv_n: float
    cpa_n: float
    economy_n: float


@dataclass(frozen=True, slots=True)
class OptimumScoredRow(Generic[T]):
    """Точка профиля с conv, CPO заказа и score для OPTIMUM."""

    row: T
    conv: float
    cpo: float
    score: float
    conv_n: float
    economy_n: float


def order_cpo_from_bid(*, bid: float, conv_views_to_orders: float) -> float | None:
    """CPO заказа на ставке (как ``predicted_pay_for_order_from_point`` / V3 MIN)."""
    if conv_views_to_orders <= 0 or bid <= 0:
        return None
    orders = calc_orders_per_1000_rub(float(conv_views_to_orders), float(bid))
    if orders is None:
        return None
    result = calc_pay_for_order(orders)
    return None if result is None else float(result)


def normalized_point_metrics(
    conv: float,
    cpo: float,
    *,
    conv_min: float,
    conv_max: float,
    cpo_min: float,
    cpo_max: float,
) -> NormalizedPointMetrics:
    """conv_n и economy_n на диапазоне профиля; при ``cpo_max == cpo_min``: ``cpa_n=0``, ``economy_n=1``."""
    if conv_max == conv_min:
        conv_n = 1.0
    else:
        conv_n = (conv - conv_min) / (conv_max - conv_min)
    if cpo_max == cpo_min:
        cpa_n = 0.0
        economy_n = 1.0
    else:
        cpa_n = (cpo - cpo_min) / (cpo_max - cpo_min)
        economy_n = 1.0 - cpa_n
    return NormalizedPointMetrics(
        conv_n=float(conv_n),
        cpa_n=float(cpa_n),
        economy_n=float(economy_n),
    )


def optimum_score_from_metrics(
    metrics: NormalizedPointMetrics,
    mode: OptimumScoreMode | Literal["current", "A", "B"] = OptimumScoreMode.CURRENT,
) -> float:
    """Скор OPTIMUM для нормализованных метрик точки."""
    if isinstance(mode, str):
        mode = OptimumScoreMode(mode)
    conv_n = metrics.conv_n
    economy_n = metrics.economy_n
    balance = OPTIMUM_CONV_WEIGHT * conv_n + OPTIMUM_ECONOMY_WEIGHT * economy_n
    center_bonus = 1.0 - abs(conv_n - economy_n)

    if mode == OptimumScoreMode.CURRENT:
        return balance
    if mode == OptimumScoreMode.VARIANT_A:
        return (
            VARIANT_A_BALANCE_WEIGHT * balance
            + VARIANT_A_CENTER_WEIGHT * center_bonus
        )
    distance = (1.0 - conv_n) ** 2 + (1.0 - economy_n) ** 2
    return -distance + VARIANT_B_CENTER_WEIGHT * center_bonus


def normalized_optimum_score(
    conv: float,
    cpo: float,
    *,
    conv_min: float,
    conv_max: float,
    cpo_min: float,
    cpo_max: float,
    mode: OptimumScoreMode | Literal["current", "A", "B"] = OptimumScoreMode.CURRENT,
) -> float:
    """Обёртка: нормализация + optimum_score для режима ``mode``."""
    metrics = normalized_point_metrics(
        conv,
        cpo,
        conv_min=conv_min,
        conv_max=conv_max,
        cpo_min=cpo_min,
        cpo_max=cpo_max,
    )
    return optimum_score_from_metrics(metrics, mode)


def score_optimum_rows(
    rows: list[tuple[T, float, float]],
    *,
    mode: OptimumScoreMode | Literal["current", "A", "B"] = OptimumScoreMode.CURRENT,
) -> list[OptimumScoredRow[T]]:
    """Посчитать score для ``(row, conv, cpo)``; пустой список → ``[]``."""
    if not rows:
        return []
    convs = [conv for _, conv, _ in rows]
    cpos = [cpo for _, _, cpo in rows]
    conv_min, conv_max = min(convs), max(convs)
    cpo_min, cpo_max = min(cpos), max(cpos)
    scored: list[OptimumScoredRow[T]] = []
    for row, conv, cpo in rows:
        metrics = normalized_point_metrics(
            conv,
            cpo,
            conv_min=conv_min,
            conv_max=conv_max,
            cpo_min=cpo_min,
            cpo_max=cpo_max,
        )
        score = optimum_score_from_metrics(metrics, mode)
        scored.append(
            OptimumScoredRow(
                row=row,
                conv=conv,
                cpo=cpo,
                score=score,
                conv_n=metrics.conv_n,
                economy_n=metrics.economy_n,
            )
        )
    return scored


def _row_bid_position(row: T) -> tuple[float, int]:
    """position/bid для tie-break (PositionProfilePoint, BidPosition, …)."""
    rp = cast(_HasPositionBid, row)
    return float(rp.bid), int(rp.position)


def _optimum_tie_key(s: OptimumScoredRow[T]) -> tuple[float, float, float, int]:
    """При равном score (±EPS) — более экономичная точка."""
    bid, position = _row_bid_position(s.row)
    return (
        round(s.score / OPTIMUM_SCORE_EPS) * OPTIMUM_SCORE_EPS,
        -s.cpo,
        -bid,
        -position,
    )


def select_optimum_row(
    rows: list[tuple[T, float, float]],
    *,
    mode: OptimumScoreMode | Literal["current", "A", "B"] = OptimumScoreMode.CURRENT,
    exclude_max_row: T | None = None,
) -> OptimumScoredRow[T] | None:
    """Лучшая точка OPTIMUM: max score; tie — меньший CPO, bid, position.

    ``exclude_max_row`` — только для экспериментов; в проде используйте ``mode=VARIANT_A``.
    """
    pool = rows
    if exclude_max_row is not None and len(rows) > 1:
        ex_key = _row_bid_position(exclude_max_row)
        filtered = [r for r in rows if _row_bid_position(r[0]) != ex_key]
        if filtered:
            pool = filtered

    scored = score_optimum_rows(pool, mode=mode)
    if not scored:
        return None
    return max(scored, key=_optimum_tie_key)


def select_optimum_row_cpo_cap(
    rows: list[tuple[T, float, float]],
    *,
    max_cpo_penalty: float,
) -> OptimumScoredRow[T] | None:
    """OPTIMUM с CPO-cap относительно MIN; balance на отфильтрованном пуле.

    1. ``min_cpo = min(CPO)`` по usable-точкам.
    2. Пул: ``CPO <= min_cpo * max_cpo_penalty``.
    3. На пуле — ``score_optimum_rows(..., mode=CURRENT)`` (balance).
    4. Пустой пул → одна точка глобального min CPO.

    Args:
        rows: ``(row, conv_carts_per_view, cpo_order_rub)``.
        max_cpo_penalty: множитель к min CPO (compare/debug, не production).

    Returns:
        Лучшая точка в cap-пуле или ``None``.
    """
    if not rows or max_cpo_penalty <= 0:
        return None
    min_cpo = min(float(cpo) for _, _, cpo in rows)
    cap = min_cpo * float(max_cpo_penalty)
    pool = [r for r in rows if float(r[2]) <= cap + 1e-9]
    if not pool:
        pool = [
            min(
                rows,
                key=lambda t: (float(t[2]), *_row_bid_position(t[0])),
            )
        ]
    scored = score_optimum_rows(pool, mode=OptimumScoreMode.CURRENT)
    if not scored:
        return None
    return max(scored, key=_optimum_tie_key)


def select_optimum_row_production(
    rows: list[tuple[T, float, float]],
) -> OptimumScoredRow[T] | None:
    """Production OPTIMUM: balance conv/economy на всём usable-профиле."""
    return select_optimum_row(rows, mode=OptimumScoreMode.CURRENT)


def select_min_cpa_row(
    rows: list[tuple[T, float, float]],
) -> tuple[T, float] | None:
    """MIN_CPA: минимальный CPO; tie — меньшая ставка, позиция."""
    if not rows:
        return None
    best = min(
        rows,
        key=lambda t: (
            float(t[2]),
            *_row_bid_position(t[0]),
        ),
    )
    return best[0], best[2]
