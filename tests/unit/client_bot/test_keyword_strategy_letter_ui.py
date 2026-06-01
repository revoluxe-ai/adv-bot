"""Буква режима V3 в списке ключей."""

from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.keyword_strategy_ui import (
    keyword_strategy_letter,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "letter"),
    [
        (KeywordStrategyMode.OFF, "o"),
        (KeywordStrategyMode.MIN_CPA, "M"),
        (KeywordStrategyMode.OPTIMUM, "O"),
        (KeywordStrategyMode.MAX_CONVERSION, "C"),
    ],
)
def test_keyword_strategy_letter(mode: KeywordStrategyMode, letter: str) -> None:
    keyword = MagicMock()
    keyword.strategy_mode = mode
    assert keyword_strategy_letter(keyword) == letter
