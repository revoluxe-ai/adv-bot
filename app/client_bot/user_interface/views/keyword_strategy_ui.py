"""Буква и расшифровка ``KeywordStrategyMode`` для V3 (список ключей / карточка ключа)."""

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

_STRATEGY_MODE_DETAIL: dict[KeywordStrategyMode, str] = {
    KeywordStrategyMode.OFF: "OFF: лестница отключена",
    KeywordStrategyMode.MIN_CPA: "MIN_CPA: мин. оплата за корзину по позициям",
    KeywordStrategyMode.OPTIMUM: "OPTIMUM: баланс конверсии и оплаты за корзину",
    KeywordStrategyMode.MAX_CONVERSION: "MAX_CONVERSION: максимум конверсии в корзину",
}


def keyword_strategy_letter(keyword: CalculatedKeyword) -> str:
    """Одна буква режима V3 для строки ключа в списке кнопок."""
    return _STRATEGY_MODE_LETTER.get(keyword.strategy_mode, "?")


def keyword_strategy_tag(keyword: CalculatedKeyword) -> str:
    """Полное описание режима V3: буква и расшифровка (экран одного ключа)."""
    mode = keyword.strategy_mode
    letter = keyword_strategy_letter(keyword)
    detail = _STRATEGY_MODE_DETAIL.get(mode, f"неизвестный режим: {mode!r}")
    return f"{letter}({detail})"
