"""Unit tests for reusable Telegram message assertion helpers."""

from __future__ import annotations

import pytest
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.client_bot.const import TELEGRAM_CAPTION_LIMIT, TELEGRAM_TEXT_MESSAGE_LIMIT
from tests.helpers.telegram_message_asserts import (
    assert_caption_within_telegram_limit,
    assert_html_is_telegram_safe,
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
    extract_button_texts,
)

pytestmark = pytest.mark.unit


def test_message_text_at_limit_passes() -> None:
    assert_message_within_telegram_limit("a" * TELEGRAM_TEXT_MESSAGE_LIMIT)


def test_message_text_above_limit_fails() -> None:
    with pytest.raises(AssertionError, match="exceeds"):
        assert_message_within_telegram_limit("a" * (TELEGRAM_TEXT_MESSAGE_LIMIT + 1))


def test_caption_at_limit_passes() -> None:
    assert_caption_within_telegram_limit("a" * TELEGRAM_CAPTION_LIMIT)


def test_caption_above_limit_fails() -> None:
    with pytest.raises(AssertionError, match="exceeds"):
        assert_caption_within_telegram_limit("a" * (TELEGRAM_CAPTION_LIMIT + 1))


def test_plain_text_is_valid_telegram_html() -> None:
    assert_html_is_telegram_safe("Привет, мир! 🚀")


def test_valid_telegram_html_passes() -> None:
    assert_html_is_telegram_safe(
        '<b>Жирный</b> <i>курсив</i> <code>123</code> '
        '<a href="https://example.com">ссылка</a>'
    )


def test_unclosed_html_tag_fails() -> None:
    with pytest.raises(AssertionError, match="Unclosed"):
        assert_html_is_telegram_safe("<b>broken")


def test_mismatched_html_tag_fails() -> None:
    with pytest.raises(AssertionError, match="Mismatched"):
        assert_html_is_telegram_safe("<b>broken</i>")


def test_unknown_html_tag_fails() -> None:
    with pytest.raises(AssertionError, match="Unsupported"):
        assert_html_is_telegram_safe("<span>bad</span>")


def test_extract_button_texts_from_inline_keyboard() -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="One", callback_data="1")]]
    )
    assert extract_button_texts(keyboard) == ["One"]


def test_extract_button_texts_from_reply_keyboard() -> None:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Contact", request_contact=True)]]
    )
    assert extract_button_texts(keyboard) == ["Contact"]


def test_assert_keyboard_has_buttons_passes() -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="A", callback_data="a")]]
    )
    assert_keyboard_has_buttons(keyboard, ["A"])


def test_assert_message_contains_required_phrases_fails_on_missing() -> None:
    with pytest.raises(AssertionError, match="Missing required phrases"):
        assert_message_contains_required_phrases("hello", ["hello", "world"])


def test_assert_no_raw_technical_text_rejects_traceback() -> None:
    with pytest.raises(AssertionError, match="Suspicious technical text"):
        assert_no_raw_technical_text("Traceback (most recent call last): boom")
