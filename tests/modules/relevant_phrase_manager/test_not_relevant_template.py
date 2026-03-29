"""Unit tests for NotRelevantTemplate (quoted exact + regex rules)."""

import logging
import time

import pytest

from app.modules.relevant_phrase_manager.not_relevante_template import NotRelevantTemplate
from app.modules.relevant_phrase_manager.relevant_phrase_template import (
    RelevantPhraseTemplate,
)


def test_empty_template_all_relevant() -> None:
    t = NotRelevantTemplate([])
    assert t.is_relevant("anything") is True


def test_empty_and_whitespace_rows_ignored() -> None:
    t = NotRelevantTemplate(["", "   ", "zzz"])
    assert t.is_relevant("spam here") is True
    assert t.is_relevant("my zzz") is False


def test_quoted_exact_match_case_insensitive() -> None:
    t = NotRelevantTemplate(['"Foo Bar"'])
    assert t.is_relevant("foo bar") is False
    assert t.is_relevant("Foo Bar") is False
    assert t.is_relevant("foo bar extra") is True


def test_quoted_does_not_substring_match() -> None:
    t = NotRelevantTemplate(['"foo"'])
    assert t.is_relevant("foo") is False
    assert t.is_relevant("foobar") is True


def test_quoted_heuristic_leading_quote_only() -> None:
    t = NotRelevantTemplate(['"partial'])
    assert t.is_relevant("partial") is False
    assert t.is_relevant("partialx") is True


def test_quoted_heuristic_trailing_quote_only() -> None:
    t = NotRelevantTemplate(['partial"'])
    assert t.is_relevant("partial") is False


def test_regex_substring_case_insensitive() -> None:
    t = NotRelevantTemplate([r"летн"])
    assert t.is_relevant("платье ЛЕТНее") is False
    assert t.is_relevant("зимнее платье") is True


def test_regex_alternation() -> None:
    t = NotRelevantTemplate([r"дешев|подделк"])
    assert t.is_relevant("очень дешево") is False
    assert t.is_relevant("подделка") is False
    assert t.is_relevant("качественно") is True


def test_regex_anchor_full_string() -> None:
    t = NotRelevantTemplate([r"^exact$"])
    assert t.is_relevant("exact") is False
    assert t.is_relevant("not exact") is True


def test_multiple_rules_or_semantics() -> None:
    t = NotRelevantTemplate(["a", "b"])
    assert t.is_relevant("xa") is False
    assert t.is_relevant("xb") is False
    assert t.is_relevant("xc") is True


def test_invalid_regex_skipped_warning(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    t = NotRelevantTemplate([r"(?P<unclosed", "valid"])
    assert t.is_relevant("valid") is False
    assert t.is_relevant("other") is True
    assert any("шаблоне НРФ" in r.message for r in caplog.records)


def test_single_quotes_exact() -> None:
    t = NotRelevantTemplate(["'foo'"])
    assert t.is_relevant("foo") is False
    assert t.is_relevant("Foo") is False


def test_redos_prone_pattern_completes_quickly() -> None:
    """RE2 must not exhibit exponential backtracking like Python re on (a+)+b."""
    t = NotRelevantTemplate([r"(a+)+b"])
    start = time.perf_counter()
    assert t.is_relevant("a" * 50 + "c") is True
    assert time.perf_counter() - start < 0.5


def test_oversized_pattern_skipped(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    long_pat = "x" * 600
    t = NotRelevantTemplate([long_pat, "z"])
    assert t.is_relevant("x" * 600) is True
    assert t.is_relevant("az") is False
    assert any("слишком длинного" in r.message for r in caplog.records)


def test_legacy_any_prefix_requires_token_per_group() -> None:
    """any:a,b — фраза нерелевантна, если ни один токен группы не входит как подстрока."""
    t = NotRelevantTemplate(["any:word1,word2"])
    assert t.is_relevant("слово word1 здесь") is True
    assert t.is_relevant("другое") is False
    assert t.is_relevant("WORD2") is True


def test_legacy_any_multiple_groups_and() -> None:
    t = NotRelevantTemplate(["any:aa", "any:bb"])
    assert t.is_relevant("aa x") is False
    assert t.is_relevant("bb x") is False
    assert t.is_relevant("aa bb") is True


def test_legacy_not_prefix_substring_not_regex() -> None:
    """not:cheap — литеральное вхождение, не regex (точка не «любой символ»)."""
    t = NotRelevantTemplate(["not:cheap"])
    assert t.is_relevant("buy cheap") is False
    assert t.is_relevant("buy cheapy") is False
    assert t.is_relevant("buy che p") is True


def test_legacy_not_prefix_quoted_exact() -> None:
    t = NotRelevantTemplate(['not:"foo bar"'])
    assert t.is_relevant("foo bar") is False
    assert t.is_relevant("foo bar x") is True


def test_legacy_any_line_not_compiled_as_regex() -> None:
    """Раньше any:… попадал в regex и не работал как задумано."""
    t = NotRelevantTemplate(["any:x"])
    assert t.is_relevant("prefix xsuffix") is True
    assert t.is_relevant("no match") is False


def test_relevant_template_legacy_not_substring_matches() -> None:
    t = RelevantPhraseTemplate(["not:deal"])
    assert t.matches("great deal") is True
    assert t.matches("other") is False


def test_relevant_template_legacy_any_or_within_row() -> None:
    t = RelevantPhraseTemplate(["any:one,two"])
    assert t.matches("the one") is True
    assert t.matches("two") is True
    assert t.matches("three") is False
