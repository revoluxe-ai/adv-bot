"""Unit tests for NotRelevantTemplate (quoted exact + regex rules)."""

import logging

import pytest

from app.modules.relevant_phrase_manager.not_relevante_template import NotRelevantTemplate


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
    assert any("невалидного regex" in r.message for r in caplog.records)


def test_single_quotes_exact() -> None:
    t = NotRelevantTemplate(["'foo'"])
    assert t.is_relevant("foo") is False
    assert t.is_relevant("Foo") is False
