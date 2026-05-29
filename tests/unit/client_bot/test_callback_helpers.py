"""Unit-тесты safe_callback_answer и middleware для inline callback."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Update, User

from app.client_bot.callback_helpers import (
    CALLBACK_PRE_ANSWERED_KEY,
    ImmediateCallbackAnswerUpdateMiddleware,
    SafeCallbackAnswerMiddleware,
    is_benign_callback_answer_error,
    safe_callback_answer,
    should_skip_immediate_callback_answer,
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


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("ts:open", True),
        ("menu:adv:1", False),
        (None, False),
    ],
)
def test_should_skip_immediate_callback_answer(data: str | None, expected: bool) -> None:
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = data
    assert should_skip_immediate_callback_answer(callback) is expected


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


@pytest.mark.asyncio
async def test_immediate_callback_answer_update_middleware_sets_flag() -> None:
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "menu:1"
    callback.from_user = User(id=1, is_bot=False, first_name="u")
    callback.answer = AsyncMock(return_value=True)

    update = Update(update_id=1, callback_query=callback)
    middleware = ImmediateCallbackAnswerUpdateMiddleware()
    data: dict[str, object] = {}
    inner = AsyncMock(return_value="ok")

    result = await middleware(inner, update, data)

    assert result == "ok"
    callback.answer.assert_awaited_once()
    assert data[CALLBACK_PRE_ANSWERED_KEY] is True
    inner.assert_awaited_once()


@pytest.mark.asyncio
async def test_immediate_callback_answer_skips_time_settings_prefix() -> None:
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "ts:open"
    callback.from_user = User(id=1, is_bot=False, first_name="u")
    callback.answer = AsyncMock(return_value=True)

    update = Update(update_id=1, callback_query=callback)
    middleware = ImmediateCallbackAnswerUpdateMiddleware()
    data: dict[str, object] = {}
    inner = AsyncMock(return_value="ok")

    await middleware(inner, update, data)

    callback.answer.assert_not_called()
    assert CALLBACK_PRE_ANSWERED_KEY not in data


@pytest.mark.asyncio
async def test_safe_callback_answer_middleware_skips_when_pre_answered() -> None:
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "menu:1"
    callback.from_user = User(id=1, is_bot=False, first_name="u")
    callback.answer = AsyncMock(return_value=True)

    middleware = SafeCallbackAnswerMiddleware(pre=True, text="Запрос в обработке")
    inner = AsyncMock(return_value="handled")
    data: dict[str, object] = {CALLBACK_PRE_ANSWERED_KEY: True}

    result = await middleware(inner, callback, data)

    assert result == "handled"
    callback.answer.assert_not_called()
    inner.assert_awaited_once()


def test_install_client_bot_dispatcher_middleware_inserts_after_errors() -> None:
    from app.client_bot.callback_helpers import (
        ImmediateCallbackAnswerUpdateMiddleware,
        install_client_bot_dispatcher_middleware,
    )

    dp = Dispatcher()
    errors_count_before = len(dp.update.outer_middleware)
    install_client_bot_dispatcher_middleware(dp)
    middlewares = dp.update.outer_middleware._middlewares  # noqa: SLF001

    assert len(middlewares) == errors_count_before + 1
    assert isinstance(middlewares[1], ImmediateCallbackAnswerUpdateMiddleware)
