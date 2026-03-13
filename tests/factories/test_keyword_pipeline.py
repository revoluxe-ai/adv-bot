"""Tests for keyword_pipeline factories and KeywordsWithBest contract."""

import pytest

from tests.factories.keyword_pipeline import (
    generate_keywords_with_best,
    KeywordsWithBest,
)


@pytest.mark.unit
class TestKeywordsWithBest:
    """Ensure KeywordsWithBest exposes .best as documented."""

    def test_generate_keywords_with_best_returns_object_with_best(self) -> None:
        """result.best must be the keyword with highest rating (docstring contract)."""
        result = generate_keywords_with_best(count=3)
        assert isinstance(result, KeywordsWithBest)
        assert len(result.keywords) == 3
        best = result.best
        assert best is not None
        assert best in result.keywords
        max_rating = max(kw.rating or 0 for kw in result.keywords)
        assert (best.rating or 0) == max_rating

    def test_keywords_with_best_empty_list_best_is_none(self) -> None:
        """Empty keywords list => .best is None."""
        result = KeywordsWithBest([])
        assert result.best is None
        assert result.keywords == []
