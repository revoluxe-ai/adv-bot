"""Unit tests for shared WB token permission copy."""

from __future__ import annotations

from app.client_bot.const import FULL_ACCESS_WB_TOKEN_REQUIRED_SCOPES
from app.client_bot.user_interface.utils.token_permissions_text import (
    format_required_wb_token_scopes,
)
from tests.helpers.telegram_message_asserts import (
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


def test_required_wb_token_scopes_formatter_uses_shared_const() -> None:
    """Formatter should render the shared full-access scopes in user-facing order."""
    assert FULL_ACCESS_WB_TOKEN_REQUIRED_SCOPES == (
        "Контент",
        "Статистика",
        "Аналитика",
        "Продвижение",
    )

    text = format_required_wb_token_scopes()
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Нужные права токена",
            "Контент",
            "Статистика",
            "Аналитика",
            "Продвижение",
        ],
    )
    assert "Контект" not in text
    assert_no_raw_technical_text(text)
