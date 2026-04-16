"""Unit-тесты для ReturnToStart middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiogram.types import Message

from app.client_bot.middlewars.return_to_start_from_state import ReturnToStart


@pytest.mark.asyncio
async def test_return_to_start_document_without_text_calls_next_handler() -> None:
    """Сообщение с документом и без text/caption не падает и пробрасывает в handler."""
    mw = ReturnToStart()
    handler = AsyncMock(return_value="next")
    msg = MagicMock(spec=Message)
    msg.text = None
    msg.caption = None
    msg.document = MagicMock()
    data: dict = {"bot": MagicMock(), "state": MagicMock()}

    result = await mw(handler, msg, data)

    handler.assert_awaited_once_with(msg, data)
    assert result == "next"


@pytest.mark.asyncio
@patch(
    "app.client_bot.middlewars.return_to_start_from_state.start_registration",
    new_callable=AsyncMock,
)
async def test_return_to_start_in_text_triggers_registration(
    mock_start_registration: AsyncMock,
) -> None:
    msg = MagicMock(spec=Message)
    msg.text = "/start"
    msg.caption = None
    next_handler = AsyncMock()
    data: dict = {"bot": MagicMock(), "state": MagicMock()}
    state = data["state"]
    state.clear = AsyncMock()

    await ReturnToStart()(next_handler, msg, data)

    state.clear.assert_awaited_once()
    mock_start_registration.assert_awaited_once_with(msg, data["bot"], state)
    next_handler.assert_not_awaited()


@pytest.mark.asyncio
@patch(
    "app.client_bot.middlewars.return_to_start_from_state.start_registration",
    new_callable=AsyncMock,
)
async def test_return_to_start_in_caption_triggers_registration(
    mock_start_registration: AsyncMock,
) -> None:
    """Команда только в подписи к медиа обрабатывается как /start."""
    msg = MagicMock(spec=Message)
    msg.text = None
    msg.caption = "/start"
    next_handler = AsyncMock()
    data: dict = {"bot": MagicMock(), "state": MagicMock()}
    state = data["state"]
    state.clear = AsyncMock()

    await ReturnToStart()(next_handler, msg, data)

    state.clear.assert_awaited_once()
    mock_start_registration.assert_awaited_once_with(msg, data["bot"], state)
    next_handler.assert_not_awaited()
