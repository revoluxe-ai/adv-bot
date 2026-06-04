"""Unit-тесты немедленного ACK callback на Dispatcher."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Update, User

from app.client_bot.middlewars.immediate_callback_answer import (
    ImmediateCallbackAnswerUpdateMiddleware,
    is_stale_callback_answer_error,
    safe_callback_query_answer,
)


def test_is_stale_callback_answer_error() -> None:
    exc = TelegramBadRequest(
        method="answerCallbackQuery",
        message="Bad Request: query is too old and response timeout expired",
    )
    assert is_stale_callback_answer_error(exc) is True


@pytest.mark.asyncio
async def test_safe_callback_query_answer_swallows_stale() -> None:
    cq = MagicMock(spec=CallbackQuery)
    cq.id = "cq-1"
    cq.data = "test"
    cq.from_user = None
    cq.answer = AsyncMock(
        side_effect=TelegramBadRequest(
            method="answerCallbackQuery",
            message="query is too old",
        )
    )
    ok = await safe_callback_query_answer(cq, text="Запрос в обработке")
    assert ok is False
    cq.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_immediate_middleware_answers_before_handler() -> None:
    order: list[str] = []

    async def inner_handler(_event: object, _data: dict[str, object]) -> None:
        order.append("handler")

    cq = MagicMock(spec=CallbackQuery)
    cq.data = "v3_tick_report_back:42"
    cq.id = "1"
    cq.from_user = User(id=99, is_bot=False, first_name="t")
    cq.answer = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = cq

    mw = ImmediateCallbackAnswerUpdateMiddleware()
    await mw(inner_handler, update, {})

    assert order == ["handler"]
    cq.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_immediate_middleware_answers_ts_prefix() -> None:
    """ts: без матча хендлера всё равно получает pre-ACK на Dispatcher."""
    cq = MagicMock(spec=CallbackQuery)
    cq.data = "ts:open:1:2"
    cq.id = "2"
    cq.from_user = User(id=1, is_bot=False, first_name="t")
    cq.answer = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = cq

    mw = ImmediateCallbackAnswerUpdateMiddleware()
    await mw(AsyncMock(), update, {})

    cq.answer.assert_awaited_once()
