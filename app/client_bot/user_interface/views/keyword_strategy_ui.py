"""Буква ``KeywordStrategyMode`` для V3 (список ключей)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

_STRATEGY_MODE_LETTER: dict[KeywordStrategyMode, str] = {
    KeywordStrategyMode.OFF: "o",
    KeywordStrategyMode.MIN_CPA: "M",
    KeywordStrategyMode.OPTIMUM: "O",
    KeywordStrategyMode.MAX_CONVERSION: "C",
}

def strategy_mode_letter(mode: KeywordStrategyMode) -> str:
    """Буква режима V3 по ``KeywordStrategyMode``."""
    return _STRATEGY_MODE_LETTER.get(mode, "?")


def keyword_strategy_letter(keyword: CalculatedKeyword) -> str:
    """Одна буква режима V3 для строки ключа в списке кнопок."""
    return strategy_mode_letter(keyword.strategy_mode)
