"""Unit tests for admin error report chunking and assembly."""

from __future__ import annotations

import typing
from unittest.mock import AsyncMock, MagicMock

import pytest

from app import client_bot as tb
from app.client_bot.user_interface.handlers import exceptions as exc_mod

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_send_text_chunks_splits_and_reconstructs() -> None:
    sent_chunks: list[str] = []

    async def send_message(chat_id: int, text: str, **_kw: object) -> MagicMock:
        assert chat_id == 999
        sent_chunks.append(text)
        return MagicMock()

    bot = MagicMock()
    bot.send_message = AsyncMock(side_effect=send_message)

    original = "A" * (tb.const.MAX_MESSAGE_LENGTH + 500)
    await exc_mod._send_text_chunks(typing.cast(typing.Any, bot), 999, original)

    assert len(sent_chunks) >= 2
    assert "".join(sent_chunks) == original


@pytest.mark.asyncio
async def test_send_admin_error_report_section_order() -> None:
    captured: list[str] = []

    async def capture_chunks(
        bot: typing.Any, chat_id: int, full_text: str
    ) -> None:
        captured.append(full_text)

    bot = MagicMock()
    monkey = pytest.MonkeyPatch()
    monkey.setattr(exc_mod, "_send_text_chunks", capture_chunks)
    monkey.setattr(exc_mod, "admin_telegram_id", 111)
    try:
        await exc_mod.send_admin_error_report(
            typing.cast(typing.Any, bot),
            headline="H1",
            extra="E1",
            brief_trace_app_lines="app line",
            traceback_text="TB",
            footer="foot",
        )
    finally:
        monkey.undo()

    assert len(captured) == 1
    text = captured[0]
    assert text.startswith("H1")
    assert text.index("--- extra ---") < text.index("--- app lines ---")
    assert text.index("--- app lines ---") < text.index("--- full traceback ---")
    assert text.index("--- full traceback ---") < text.index("--- footer ---")
    assert "E1" in text
    assert "app line" in text
    assert "TB" in text
    assert "foot" in text


@pytest.mark.asyncio
async def test_send_admin_error_report_no_app_lines_uses_extra() -> None:
    captured: list[str] = []

    async def capture_chunks(
        bot: typing.Any, chat_id: int, full_text: str
    ) -> None:
        captured.append(full_text)

    bot = MagicMock()
    monkey = pytest.MonkeyPatch()
    monkey.setattr(exc_mod, "_send_text_chunks", capture_chunks)
    monkey.setattr(exc_mod, "admin_telegram_id", 222)
    try:
        await exc_mod.send_admin_error_report(
            typing.cast(typing.Any, bot),
            headline="Unhandled exception in client bot handler",
            traceback_text="trace body",
            extra="Строки с названием пакета 'app' в трейсе не найдены.",
            brief_trace_app_lines=None,
            footer="Ник пользователя: x",
        )
    finally:
        monkey.undo()

    assert len(captured) == 1
    assert "--- app lines ---" not in captured[0]
    assert "app' в трейсе не найдены" in captured[0]
