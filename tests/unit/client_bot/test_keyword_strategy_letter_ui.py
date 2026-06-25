"""Буква режима V3 в списке ключей."""

from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.keyword_strategy_ui import (
    LETTER_GAP,
    LETTER_PFO,
    keyword_strategy_letter,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


def _keyword_mock(
    *,
    mode: KeywordStrategyMode,
    position_profile: list[object] | None,
    pay_for_order: float | None,
) -> MagicMock:
    keyword = MagicMock()
    keyword.strategy_mode = mode
    keyword.position_profile = position_profile
    keyword.pay_for_order = pay_for_order
    return keyword


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
def test_keyword_strategy_letter_with_profile(
    mode: KeywordStrategyMode, letter: str
) -> None:
    keyword = _keyword_mock(
        mode=mode,
        position_profile=[MagicMock()],
        pay_for_order=50.0,
    )
    assert keyword_strategy_letter(keyword) == letter


@pytest.mark.unit
def test_keyword_strategy_letter_pfo_always_n() -> None:
    for mode in (
        KeywordStrategyMode.OFF,
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
    ):
        keyword = _keyword_mock(
            mode=mode,
            position_profile=None,
            pay_for_order=42.0,
        )
        assert keyword_strategy_letter(keyword) == LETTER_PFO


@pytest.mark.unit
def test_keyword_strategy_letter_gap_always_g() -> None:
    for mode in (KeywordStrategyMode.OFF, KeywordStrategyMode.MIN_CPA):
        keyword = _keyword_mock(
            mode=mode,
            position_profile=None,
            pay_for_order=None,
        )
        assert keyword_strategy_letter(keyword) == LETTER_GAP

    keyword_zero = _keyword_mock(
        mode=KeywordStrategyMode.OFF,
        position_profile=None,
        pay_for_order=0.0,
    )
    assert keyword_strategy_letter(keyword_zero) == LETTER_GAP
