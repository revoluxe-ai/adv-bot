"""Tests for phrases_processor white-list helpers."""

from unittest.mock import patch

import pytest

from app.modules.wb_adv_updater import phrases_processor
from tests.factories.keyword_pipeline import (
    CalculatedKeywordFactory,
    HardStatus,
)


@pytest.mark.unit
class TestGetMinRating:
    """get_min_rating учитывает только ключи с определённым rating (не None)."""

    def test_returns_min_among_white_list_with_defined_ratings(self) -> None:
        """Минимум среди ключей в белом списке с заданным рейтингом."""
        kw_low = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            rating=10.0,
        )
        kw_high = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            rating=50.0,
        )
        result = phrases_processor.get_min_rating([kw_low, kw_high])
        assert result == 10.0

    def test_ignores_keywords_with_rating_none(self) -> None:
        """Ключи с rating is None не участвуют в расчёте минимума."""
        kw_with_rating = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            rating=15.0,
        )
        kw_none_rating = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            rating=99.0,
        )
        with patch.object(kw_none_rating, "rating", None):
            result = phrases_processor.get_min_rating([kw_with_rating, kw_none_rating])
        assert result == 15.0

    def test_returns_none_when_all_white_list_have_rating_none(self) -> None:
        """Если у всех в белом списке rating is None — возвращаем None."""
        kw1 = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            rating=10.0,
        )
        kw2 = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            rating=20.0,
        )
        with patch.object(kw1, "rating", None), patch.object(kw2, "rating", None):
            result = phrases_processor.get_min_rating([kw1, kw2])
        assert result is None

    def test_returns_none_for_empty_white_list(self) -> None:
        """Нет ключей в белом списке — None."""
        kw = CalculatedKeywordFactory.build(keyword_setting__hard_status=HardStatus.BLACKLIST)
        result = phrases_processor.get_min_rating([kw])
        assert result is None

    def test_ignores_non_white_list(self) -> None:
        """Учитываются только hard_status == 2 (белый список)."""
        kw_white = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            rating=5.0,
        )
        kw_black = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.BLACKLIST,
            rating=1.0,
        )
        result = phrases_processor.get_min_rating([kw_white, kw_black])
        assert result == 5.0
