"""Буквы режима V3 в списке ключей Telegram (UI only).

FULL (есть CH ``position_profile``): ``o`` / ``M`` / ``O`` / ``C`` по ``KeywordStrategyMode``.
Без матрицы: GAP → ``G``, PFO → ``N`` — подмена только в списке кнопок, updater не затрагивается.
Перед отрисовкой списка V3 ``sort_keywords_for_v3_ui`` подставляет ``position_profile`` из CH
(без второго ``fetch_keywords_from_database``).
Карточка ключа использует ``strategy_mode_letter`` без tier-подмены.
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

LETTER_GAP = "G"
LETTER_PFO = "N"

_STRATEGY_MODE_LETTER: dict[KeywordStrategyMode, str] = {
    KeywordStrategyMode.OFF: "o",
    KeywordStrategyMode.MIN_CPA: "M",
    KeywordStrategyMode.OPTIMUM: "O",
    KeywordStrategyMode.MAX_CONVERSION: "C",
}


def strategy_mode_letter(mode: KeywordStrategyMode) -> str:
    """Буква режима V3 по ``KeywordStrategyMode`` (карточка ключа, лестница)."""
    return _STRATEGY_MODE_LETTER.get(mode, "?")


def keyword_strategy_letter(keyword: CalculatedKeyword) -> str:
    """Одна буква для строки ключа в списке: tier N/G без матрицы, иначе режим."""
    if bool(keyword.position_profile):
        return strategy_mode_letter(keyword.strategy_mode)
    if is_keyword_no_data(keyword):
        return LETTER_GAP
    return LETTER_PFO
