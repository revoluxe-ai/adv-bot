"""Reusable assertions for Telegram message and keyboard regression tests."""

from __future__ import annotations

from html.parser import HTMLParser
import re
from typing import Any

from app.client_bot.const import TELEGRAM_CAPTION_LIMIT, TELEGRAM_TEXT_MESSAGE_LIMIT

_ALLOWED_TELEGRAM_TAGS = {
    "a",
    "b",
    "code",
    "del",
    "em",
    "i",
    "ins",
    "pre",
    "s",
    "strike",
    "strong",
    "u",
}
_SUSPICIOUS_TEXT_PATTERNS = [
    r"Traceback \(most recent call last\):",
    r"callback_data=",
    r"\b(?:adv|gate|shop|choice_adv_paginator|partner_admin|check_subscribe):[A-Za-z0-9_:-]+\b",
    r"\b[A-Z][A-Za-z0-9_]+\.[A-Z_]{2,}\b",
    r"\b(?:Exception|RuntimeError|ValueError|TypeError):",
]


class _TelegramHtmlValidator(HTMLParser):
    """Minimal Telegram-oriented HTML validator for user-facing texts."""

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag not in _ALLOWED_TELEGRAM_TAGS:
            msg = f"Unsupported Telegram HTML tag: <{tag}>"
            raise AssertionError(msg)
        if tag == "a":
            attr_names = {name for name, _ in attrs}
            if attr_names != {"href"}:
                raise AssertionError("<a> must contain only the href attribute")
            href_value = next((value for name, value in attrs if name == "href"), None)
            if not href_value:
                raise AssertionError("<a> requires a non-empty href attribute")
        elif attrs:
            msg = f"Tag <{tag}> must not have attributes in Telegram-safe HTML"
            raise AssertionError(msg)
        self._stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in _ALLOWED_TELEGRAM_TAGS:
            msg = f"Unsupported Telegram HTML closing tag: </{tag}>"
            raise AssertionError(msg)
        if not self._stack:
            msg = f"Unexpected closing tag: </{tag}>"
            raise AssertionError(msg)
        expected = self._stack.pop()
        if expected != tag:
            msg = f"Mismatched closing tag: expected </{expected}>, got </{tag}>"
            raise AssertionError(msg)

    def close(self) -> None:
        super().close()
        if self._stack:
            msg = f"Unclosed Telegram HTML tags: {', '.join(self._stack)}"
            raise AssertionError(msg)


def assert_message_within_telegram_limit(text: str) -> None:
    """Assert that message text does not exceed Telegram text limits."""
    if len(text) > TELEGRAM_TEXT_MESSAGE_LIMIT:
        msg = (
            f"Telegram message length {len(text)} exceeds "
            f"{TELEGRAM_TEXT_MESSAGE_LIMIT}"
        )
        raise AssertionError(msg)


def assert_caption_within_telegram_limit(text: str) -> None:
    """Assert that caption text does not exceed Telegram caption limits."""
    if len(text) > TELEGRAM_CAPTION_LIMIT:
        msg = (
            f"Telegram caption length {len(text)} exceeds "
            f"{TELEGRAM_CAPTION_LIMIT}"
        )
        raise AssertionError(msg)


def assert_message_contains_required_phrases(text: str, phrases: list[str]) -> None:
    """Assert that all required user-facing phrases are present."""
    missing = [phrase for phrase in phrases if phrase not in text]
    if missing:
        msg = f"Missing required phrases: {missing!r}"
        raise AssertionError(msg)


def extract_button_texts(keyboard: Any) -> list[str]:
    """Extract all button labels from inline or reply keyboards."""
    if keyboard is None:
        return []
    rows = getattr(keyboard, "inline_keyboard", None)
    if rows is None:
        rows = getattr(keyboard, "keyboard", None)
    if rows is None:
        msg = f"Unsupported keyboard type: {type(keyboard)!r}"
        raise AssertionError(msg)
    return [button.text for row in rows for button in row]


def assert_keyboard_has_buttons(keyboard: Any, expected_texts: list[str]) -> None:
    """Assert that the keyboard contains all expected button texts."""
    actual_texts = extract_button_texts(keyboard)
    missing = [text for text in expected_texts if text not in actual_texts]
    if missing:
        msg = f"Missing keyboard buttons: {missing!r}. Actual: {actual_texts!r}"
        raise AssertionError(msg)


def assert_no_raw_technical_text(text: str) -> None:
    """Fail on obvious raw technical/debug strings leaking into user copy."""
    for pattern in _SUSPICIOUS_TEXT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            msg = f"Suspicious technical text detected: {match.group(0)!r}"
            raise AssertionError(msg)


def assert_html_is_telegram_safe(text: str) -> None:
    """Assert that a string is safe for Telegram HTML parse mode."""
    parser = _TelegramHtmlValidator()
    parser.feed(text)
    parser.close()
