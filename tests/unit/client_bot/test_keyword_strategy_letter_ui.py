"""Буква режима V3 в списке ключей и полная расшифровка в карточке ключа."""

from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.keyword_strategy_ui import (
    keyword_strategy_letter,
    keyword_strategy_tag,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "letter", "full"),
    [
        (
            KeywordStrategyMode.OFF,
            "o",
            "o(OFF: лестница отключена)",
        ),
        (
            KeywordStrategyMode.MIN_CPA,
            "M",
            "M(MIN_CPA: мин. оплата за корзину по позициям)",
        ),
        (
            KeywordStrategyMode.OPTIMUM,
            "O",
            "O(OPTIMUM: баланс конверсии и оплаты за корзину)",
        ),
        (
            KeywordStrategyMode.MAX_CONVERSION,
            "C",
            "C(MAX_CONVERSION: максимум конверсии в корзину)",
        ),
    ],
)
def test_keyword_strategy_letter_and_tag(
    mode: KeywordStrategyMode, letter: str, full: str
) -> None:
    keyword = MagicMock()
    keyword.strategy_mode = mode
    assert keyword_strategy_letter(keyword) == letter
    assert keyword_strategy_tag(keyword) == full
