"""Немедленный ACK на CallbackQuery до FSM, Scene и GateMiddleware.

Telegram требует ответ на inline-callback в короткий срок. Роутерный
``CallbackAnswerMiddleware`` на ``global_router`` выполняется после FSM/Scene —
из-за этого часто падает ``query is too old``. Этот middleware вешается на
``Dispatcher.update.outer_middleware`` и отвечает в самом начале цепочки.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, TelegramObject, Update

logger = logging.getLogger(__name__)

_STALE_CALLBACK_MARKERS = (
    "query is too old",
    "query id is invalid",
    "response timeout expired",
)


def is_stale_callback_answer_error(exc: BaseException) -> bool:
    """True, если Telegram отклонил answer как просроченный или невалидный."""
    if not isinstance(exc, TelegramBadRequest):
        return False
    msg = (getattr(exc, "message", None) or str(exc)).lower()
    return any(marker in msg for marker in _STALE_CALLBACK_MARKERS)


async def safe_callback_query_answer(
    callback_query: CallbackQuery,
    *,
    text: str | None = None,
    show_alert: bool = False,
) -> bool:
    """Ответить на callback; при просроченном query — warning и False, без исключения.

    Returns:
        True если answer ушёл в Telegram, False если пропущен (stale/ошибка ACK).
    """
    try:
        await callback_query.answer(text=text, show_alert=show_alert)
        return True
    except TelegramBadRequest as exc:
        if is_stale_callback_answer_error(exc):
            from_user = getattr(callback_query, "from_user", None)
            logger.warning(
                "callback answer skipped (stale): id=%s data=%r user=%s",
                getattr(callback_query, "id", None),
                getattr(callback_query, "data", None),
                from_user.id if from_user is not None else None,
            )
            return False
        raise


class ImmediateCallbackAnswerUpdateMiddleware(BaseMiddleware):
    """Pre-answer на уровне Update до роутеров и FSM."""

    def __init__(self, text: str | None = "Запрос в обработке") -> None:
        self._text = text

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update) and event.callback_query is not None:
            logger.debug(
                "ImmediateCallbackAnswerUpdateMiddleware: callback received user=%s data=%r",
                event.callback_query.from_user.id,
                event.callback_query.data,
            )
            _ = await safe_callback_query_answer(event.callback_query, text=self._text)
        return await handler(event, data)
