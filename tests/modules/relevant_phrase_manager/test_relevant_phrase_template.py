"""Unit tests for RelevantPhraseTemplate (quoted exact + regex rules)."""

import logging
import time

import pytest

from app.modules.relevant_phrase_manager.relevant_phrase_template import (
    RelevantPhraseTemplate,
)


def test_empty_template_no_matches() -> None:
    t = RelevantPhraseTemplate([])
    assert t.matches("anything") is False


def test_empty_and_whitespace_rows_ignored() -> None:
    t = RelevantPhraseTemplate(["", "   ", "zzz"])
    assert t.matches("spam here") is False
    assert t.matches("my zzz") is True


def test_quoted_exact_match_case_insensitive() -> None:
    t = RelevantPhraseTemplate(['"Foo Bar"'])
    assert t.matches("foo bar") is True
    assert t.matches("Foo Bar") is True
    assert t.matches("foo bar extra") is False


def test_quoted_does_not_substring_match() -> None:
    t = RelevantPhraseTemplate(['"foo"'])
    assert t.matches("foo") is True
    assert t.matches("foobar") is False


def test_quoted_heuristic_leading_quote_only() -> None:
    t = RelevantPhraseTemplate(['"partial'])
    assert t.matches("partial") is True
    assert t.matches("partialx") is False


def test_quoted_heuristic_trailing_quote_only() -> None:
    t = RelevantPhraseTemplate(['partial"'])
    assert t.matches("partial") is True


def test_regex_substring_case_insensitive() -> None:
    t = RelevantPhraseTemplate([r"летн"])
    assert t.matches("платье ЛЕТНее") is True
    assert t.matches("зимнее платье") is False


def test_regex_alternation() -> None:
    t = RelevantPhraseTemplate([r"дешев|подделк"])
    assert t.matches("очень дешево") is True
    assert t.matches("подделка") is True
    assert t.matches("качественно") is False


def test_regex_anchor_full_string() -> None:
    t = RelevantPhraseTemplate([r"^exact$"])
    assert t.matches("exact") is True
    assert t.matches("not exact") is False


def test_multiple_rules_or_semantics() -> None:
    t = RelevantPhraseTemplate(["a", "b"])
    assert t.matches("xa") is True
    assert t.matches("xb") is True
    assert t.matches("xc") is False


def test_invalid_regex_skipped_warning(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    t = RelevantPhraseTemplate([r"(?P<unclosed", "valid"])
    assert t.matches("valid") is True
    assert t.matches("other") is False
    assert any("релевантных фраз" in r.message for r in caplog.records)


def test_single_quotes_exact() -> None:
    t = RelevantPhraseTemplate(["'foo'"])
    assert t.matches("foo") is True
    assert t.matches("Foo") is True


def test_redos_prone_pattern_completes_quickly() -> None:
    t = RelevantPhraseTemplate([r"(a+)+b"])
    start = time.perf_counter()
    assert t.matches("a" * 50 + "c") is False
    assert time.perf_counter() - start < 0.5


def test_oversized_pattern_skipped(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    long_pat = "x" * 600
    t = RelevantPhraseTemplate([long_pat, "z"])
    assert t.matches("x" * 600) is False
    assert t.matches("az") is True
    assert any("слишком длинного" in r.message for r in caplog.records)
