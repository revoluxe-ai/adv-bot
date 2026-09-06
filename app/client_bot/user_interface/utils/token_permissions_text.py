"""Shared user-facing copy for WB token permission explanations."""

from __future__ import annotations

from app.client_bot.const import FULL_ACCESS_WB_TOKEN_REQUIRED_SCOPES


def format_required_wb_token_scopes() -> str:
    """Return the required WB token scopes as a user-facing sentence."""
    scopes_text = ", ".join(FULL_ACCESS_WB_TOKEN_REQUIRED_SCOPES)
    return f"Нужные права токена: {scopes_text}."
