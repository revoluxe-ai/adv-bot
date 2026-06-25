"""Regression tests for user-facing token result messages."""

from __future__ import annotations

from app.client_bot.user_interface.handlers.start.start import (
    _build_token_invalid_format_message,
    _build_token_read_only_added_message,
    _build_token_read_only_rejected_message,
    _build_token_success_added_message,
)
from tests.helpers.telegram_message_asserts import (
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


def test_token_invalid_message_explains_next_action() -> None:
    """Invalid token message should explain how to fix the input."""
    text = _build_token_invalid_format_message()

    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "скопирован полностью",
            "лишних пробелов",
            "токен только для чтения",
        ],
    )
    assert_no_raw_technical_text(text)


def test_token_read_only_rejected_message_explains_limits() -> None:
    """Rejected read-only token message should explain allowed and blocked behavior."""
    text = _build_token_read_only_rejected_message()

    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "токен только для чтения",
            "не будет менять рекламу",
            "токен с возможностью изменений в кабинете",
            "Нужные права токена: Контент, Статистика, Аналитика, Продвижение.",
        ],
    )
    assert "права продвижения" not in text
    assert "free" not in text.lower()
    assert_no_raw_technical_text(text)


def test_token_read_only_added_message_explains_limits() -> None:
    """Saved read-only token message should keep the same self-service guidance."""
    text = _build_token_read_only_added_message()

    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Только для чтения",
            "токен только для чтения",
            "не будет менять рекламу",
            "токен с возможностью изменений в кабинете",
            "Нужные права токена: Контент, Статистика, Аналитика, Продвижение.",
        ],
    )
    assert "права продвижения" not in text
    assert "free" not in text.lower()
    assert_no_raw_technical_text(text)


def test_token_success_message_points_to_next_step() -> None:
    """Success message should point the user to shops and campaigns."""
    text = _build_token_success_added_message("Test Shop")

    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Мои магазины",
            "рекламную кампанию",
        ],
    )
    assert_no_raw_technical_text(text)
