from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.keyboards import keyword_strategy_tag
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (KeywordStrategyMode.OFF, "o(OFF: лестница отключена)"),
        (
            KeywordStrategyMode.MIN_CPA,
            "M(MIN_CPA: мин. оплата за корзину по позициям)",
        ),
        (
            KeywordStrategyMode.OPTIMUM,
            "O(OPTIMUM: баланс конверсии и оплаты за корзину)",
        ),
        (
            KeywordStrategyMode.MAX_CONVERSION,
            "C(MAX_CONVERSION: максимум конверсии в корзину)",
        ),
    ],
)
def test_keyword_strategy_tag_mapping(mode: KeywordStrategyMode, expected: str) -> None:
    keyword = MagicMock()
    keyword.strategy_mode = mode
    assert keyword_strategy_tag(keyword) == expected
