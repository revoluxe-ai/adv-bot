"""SSOT tier ключа V3: FULL / PFO / NO DATA по ``CalculatedKeyword.pay_for_order`` и CH+conv."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)


def is_keyword_no_data(keyword: CalculatedKeyword) -> bool:
    """``True``, если на ключе нет операционного ``pay_for_order`` (NO DATA tier)."""
    pfo = keyword.pay_for_order
    return pfo is None or float(pfo) <= 0


def keyword_pfo_value(keyword: CalculatedKeyword) -> float | None:
    """Положительный ``keyword.pay_for_order`` или ``None``."""
    pfo = keyword.pay_for_order
    if pfo is None:
        return None
    value = float(pfo)
    if value <= 0:
        return None
    return value


def is_pay_for_order_gap(
    keyword: CalculatedKeyword,
    *,
    strategy_mode: KeywordStrategyMode | None = None,
) -> bool:
    """NO DATA + OFF: кандидат на enable (фаза ``plan_pay_for_order_gap_enable``)."""
    mode = strategy_mode if strategy_mode is not None else keyword.strategy_mode
    return mode == KeywordStrategyMode.OFF and is_keyword_no_data(keyword)
