"""Безопасный ответ на inline callback и ранняя установка middleware Dispatcher."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Dispatcher, loggers
from aiogram.dispatcher.flags import get_flag
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, TelegramObject, Update
from aiogram.utils.callback_answer import CallbackAnswer

logger = logging.getLogger(__name__)

CALLBACK_PRE_ANSWERED_KEY = "callback_pre_answered"
DEFAULT_CALLBACK_ANSWER_TEXT = "Запрос в обработке"

# Handlers с @flags.callback_answer(disabled=True) управляют answer сами.
_CALLBACK_DATA_SKIP_IMMEDIATE_ANSWER_PREFIXES = ("ts:",)

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


def should_skip_immediate_callback_answer(callback: CallbackQuery) -> bool:
    """True для callback_data, где handler сам отвечает с кастомным текстом."""
    data = callback.data
    if not data:
        return False
    return data.startswith(_CALLBACK_DATA_SKIP_IMMEDIATE_ANSWER_PREFIXES)


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


class ImmediateCallbackAnswerUpdateMiddleware(BaseMiddleware):
    """Отвечает на callback до UserContext/FSM (Redis), чтобы не истекал query timeout."""

    def __init__(self, text: str = DEFAULT_CALLBACK_ANSWER_TEXT) -> None:
        self._text = text

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update) and event.callback_query is not None:
            callback = event.callback_query
            if not should_skip_immediate_callback_answer(callback):
                if await safe_callback_answer(callback, text=self._text):
                    data[CALLBACK_PRE_ANSWERED_KEY] = True
        return await handler(event, data)


class SafeCallbackAnswerMiddleware(BaseMiddleware):
    """Аналог aiogram CallbackAnswerMiddleware с безопасным answer и skip после pre-answer."""

    def __init__(
        self,
        pre: bool = False,
        text: str | None = None,
        show_alert: bool | None = None,
        url: str | None = None,
        cache_time: int | None = None,
    ) -> None:
        self.pre = pre
        self.text = text
        self.show_alert = show_alert
        self.url = url
        self.cache_time = cache_time

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        if data.get(CALLBACK_PRE_ANSWERED_KEY):
            return await handler(event, data)

        callback_answer = data["callback_answer"] = self._construct_callback_answer(
            properties=get_flag(data, "callback_answer"),
        )

        if not callback_answer.disabled and callback_answer.answered:
            await self._answer(event, callback_answer)
        try:
            return await handler(event, data)
        finally:
            if not callback_answer.disabled and not callback_answer.answered:
                await self._answer(event, callback_answer)

    def _construct_callback_answer(
        self,
        properties: dict[str, Any] | bool | None,
    ) -> CallbackAnswer:
        pre, disabled, text, show_alert, url, cache_time = (
            self.pre,
            False,
            self.text,
            self.show_alert,
            self.url,
            self.cache_time,
        )
        if isinstance(properties, dict):
            pre = properties.get("pre", pre)
            disabled = properties.get("disabled", disabled)
            text = properties.get("text", text)
            show_alert = properties.get("show_alert", show_alert)
            url = properties.get("url", url)
            cache_time = properties.get("cache_time", cache_time)

        return CallbackAnswer(
            answered=pre,
            disabled=disabled,
            text=text,
            show_alert=show_alert,
            url=url,
            cache_time=cache_time,
        )

    async def _answer(
        self,
        event: CallbackQuery,
        callback_answer: CallbackAnswer,
    ) -> None:
        loggers.middlewares.info("Answer to callback query id=%s", event.id)
        await safe_callback_answer(
            event,
            text=callback_answer.text,
            show_alert=bool(callback_answer.show_alert),
            url=callback_answer.url,
            cache_time=callback_answer.cache_time,
        )


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


def install_client_bot_dispatcher_middleware(dp: Dispatcher) -> None:
    """Подключает ранний callback answer до FSM и не ломает порядок ErrorsMiddleware."""
    outer = dp.update.outer_middleware
    # ErrorsMiddleware регистрируется в Dispatcher.__init__ первым (index 0).
    outer._middlewares.insert(1, ImmediateCallbackAnswerUpdateMiddleware())  # noqa: SLF001
