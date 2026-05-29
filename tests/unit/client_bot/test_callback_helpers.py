"""Unit-тесты safe_callback_answer и классификации ошибок Telegram callback."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, User

from app.client_bot.callback_helpers import (
    is_benign_callback_answer_error,
    safe_callback_answer,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("query is too old and response timeout expired", True),
        ("Bad Request: query ID is invalid", True),
        ("query is already answered", True),
        ("message is too long", False),
    ],
)
def test_is_benign_callback_answer_error(message: str, expected: bool) -> None:
    exc = TelegramBadRequest(method=None, message=message)  # type: ignore[arg-type]
    assert is_benign_callback_answer_error(exc) is expected


@pytest.mark.asyncio
async def test_safe_callback_answer_swallows_stale_query() -> None:
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "test:data"
    callback.from_user = User(id=1, is_bot=False, first_name="u")
    callback.answer = AsyncMock(
        side_effect=TelegramBadRequest(
            method=None,  # type: ignore[arg-type]
            message="query is too old and response timeout expired",
        )
    )

    answered = await safe_callback_answer(callback)

    assert answered is False
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_safe_callback_answer_reraises_unexpected_bad_request() -> None:
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "test:data"
    callback.from_user = User(id=1, is_bot=False, first_name="u")
    callback.answer = AsyncMock(
        side_effect=TelegramBadRequest(
            method=None,  # type: ignore[arg-type]
            message="message is too long",
        )
    )

    with pytest.raises(TelegramBadRequest):
        await safe_callback_answer(callback)
