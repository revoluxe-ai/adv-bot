"""Regression tests for WB token onboarding copy."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.client_bot.user_interface.views.messages.messages import AddNewTokenGet
from tests.helpers.telegram_message_asserts import (
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


def test_add_new_token_get_explains_required_scopes_and_modes() -> None:
    """Token onboarding screen should explain read-only and full-access modes."""
    text = AddNewTokenGet(
        bot=MagicMock(),
        chat_id=1,
        cabinet_name="Test Shop",
    ).text

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
