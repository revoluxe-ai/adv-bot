"""Mapping helpers between campaign and keyword strategy enums."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums.keyword_strategy_mode import (
    KeywordStrategyMode,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy


def campaign_strategy_to_keyword_strategy_mode(
    adv_strategy: Strategy | str | None,
) -> KeywordStrategyMode:
    """Map campaign ``Strategy`` to the active keyword ``strategy_mode``."""
    if adv_strategy is None:
        return KeywordStrategyMode.MIN_CPA
    normalized = (
        adv_strategy
        if isinstance(adv_strategy, Strategy)
        else Strategy(str(adv_strategy))
    )
    mapping = {
        Strategy.MIN_CPO: KeywordStrategyMode.MIN_CPA,
        Strategy.OPTIMUM: KeywordStrategyMode.OPTIMUM,
        Strategy.MAX_CONV: KeywordStrategyMode.MAX_CONVERSION,
    }
    return mapping[normalized]
