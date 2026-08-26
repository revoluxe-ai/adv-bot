import pytest

from app.client_bot.const import TELEGRAM_TEXT_MESSAGE_LIMIT
from app.client_bot.telegram_message_split import split_telegram_plain_text


def test_empty() -> None:
    assert split_telegram_plain_text("") == []


def test_short_unchanged() -> None:
    s = "hello"
    assert split_telegram_plain_text(s, TELEGRAM_TEXT_MESSAGE_LIMIT) == [s]


def test_max_chars_invalid() -> None:
    with pytest.raises(ValueError, match="max_chars"):
        split_telegram_plain_text("a", 0)


def test_prefers_newlines_no_mid_line_when_lines_fit() -> None:
    """Chunks align to line breaks; ✓/✗ lines stay whole if they fit under the limit."""
    lines = [f"✓ подходит: phrase-{i}" for i in range(5)]
    full = "Header line\n" + "\n".join(lines)
    max_chars = 50
    chunks = split_telegram_plain_text(full, max_chars)
    assert all(len(c) <= max_chars for c in chunks)
    for chunk in chunks:
        for line in chunk.split("\n"):
            if line.startswith("✓"):
                assert "phrase-" in line


def test_all_lines_short_reconstructs_with_newline_join() -> None:
    """When no line exceeds max_chars, joining chunks with \\n restores the full text."""
    full = "a\nbb\nccc\ndddd\n"
    # strip for realistic body without trailing newline - use rstrip for test
    full = "a\nbb\nccc\ndddd"
    max_chars = 6
    chunks = split_telegram_plain_text(full, max_chars)
    assert all(len(c) <= max_chars for c in chunks)
    assert "\n".join(chunks) == full


def test_single_oversized_line_codepoint_chunks() -> None:
    full = "x" * 100
    max_chars = 30
    chunks = split_telegram_plain_text(full, max_chars)
    assert all(len(c) <= max_chars for c in chunks)
    assert "".join(chunks) == full


def test_unicode_scalar_preserved_in_line_split() -> None:
    """Slicing is on Python str (code points); single-scalar symbols stay valid."""
    full = "✓" * 80
    max_chars = 25
    chunks = split_telegram_plain_text(full, max_chars)
    assert "".join(chunks) == full
    assert all(len(c) <= max_chars for c in chunks)
