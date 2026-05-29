"""Безопасный ответ на inline callback и диагностика медленных обработчиков."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)

_CALLBACK_ANSWER_BENIGN_MARKERS = (
    "query is too old",
    "response timeout expired",
    "query id is invalid",
    "query is already answered",
)


def is_benign_callback_answer_error(exc: BaseException) -> bool:
    """True, если Telegram отклонил повторный или просроченный answer callback."""
    if not isinstance(exc, TelegramBadRequest):
        return False
    message = (getattr(exc, "message", None) or str(exc)).lower()
    return any(marker in message for marker in _CALLBACK_ANSWER_BENIGN_MARKERS)


async def safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
    url: str | None = None,
    cache_time: int | None = None,
) -> bool:
    """Ответить на callback_query; просроченные/повторные запросы не валят handler.

    Returns:
        True, если Telegram принял answer; False при просроченном/повторном answer.
    """
    try:
        await callback.answer(
            text=text,
            show_alert=show_alert,
            url=url,
            cache_time=cache_time,
        )
        return True
    except TelegramBadRequest as exc:
        if is_benign_callback_answer_error(exc):
            logger.warning(
                "Callback answer skipped: data=%s user_id=%s error=%s",
                callback.data,
                callback.from_user.id if callback.from_user else None,
                exc,
            )
            return False
        raise


class CallbackTimingMiddleware(BaseMiddleware):
    """Логирует медленные callback_query для диагностики зависаний кнопок."""

    def __init__(self, slow_threshold_sec: float = 3.0) -> None:
        self._slow_threshold_sec = slow_threshold_sec

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        started = time.monotonic()
        try:
            return await handler(event, data)
        finally:
            elapsed = time.monotonic() - started
            if elapsed >= self._slow_threshold_sec:
                handler_callback = data.get("handler")
                handler_name = getattr(handler_callback, "callback", handler_callback)
                logger.warning(
                    "slow callback handler=%s data=%s user_id=%s elapsed=%.3fs",
                    handler_name,
                    event.data,
                    event.from_user.id if event.from_user else None,
                    elapsed,
                )
