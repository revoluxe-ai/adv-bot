"""Unit tests for secret-oriented settings aliases."""

from __future__ import annotations

from app.settings.settings_master import Settings


def test_telegram_bot_token_prefers_dedicated_client_secret(
    monkeypatch,
) -> None:
    """Dedicated client bot secret must override the legacy shared token."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "legacy-token")
    monkeypatch.setenv("CLIENT_BOT_TOKEN", "client-token")

    settings = Settings()

    assert settings.TELEGRAM_BOT_TOKEN == "client-token"


def test_webhook_secret_prefers_dedicated_client_secret(monkeypatch) -> None:
    """Dedicated client webhook secret must override the legacy shared secret."""
    monkeypatch.setenv("WEBHOOK_SECRET", "legacy-webhook")
    monkeypatch.setenv("CLIENT_BOT_WEBHOOK_SECRET", "client-webhook")

    settings = Settings()

    assert settings.WEBHOOK_SECRET == "client-webhook"


def test_sender_tokens_support_dedicated_alias(monkeypatch) -> None:
    """Sender token pool can come from the dedicated alias env."""
    monkeypatch.delenv("TG_TOKENS_FOR_SENDING", raising=False)
    monkeypatch.setenv("TG_SENDER_BOT_TOKENS", "one, two ,three")

    settings = Settings()

    assert settings.TG_TOKENS_FOR_SENDING == ["one", "two", "three"]


def test_sender_tokens_prefers_dedicated_alias(monkeypatch) -> None:
    """Dedicated sender secret must override the legacy shared env."""
    monkeypatch.setenv("TG_TOKENS_FOR_SENDING", "legacy-one,legacy-two")
    monkeypatch.setenv("TG_SENDER_BOT_TOKENS", "dedicated-one,dedicated-two")

    settings = Settings()

    assert settings.TG_TOKENS_FOR_SENDING == ["dedicated-one", "dedicated-two"]
