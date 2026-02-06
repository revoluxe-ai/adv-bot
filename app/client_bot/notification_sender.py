"""Notification sender that cycles through multiple Telegram bots."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.settings import settings

logger = logging.getLogger(__name__)


class NotificationSender:
    """Send Telegram messages using a pool of bots."""

    def __init__(
        self,
        tokens: list[str],
        bot_factory: Callable[[str], Bot] | None = None,
    ) -> None:
        if not tokens:
            raise ValueError("At least one token is required to send notifications")

        self._tokens = list(tokens)
        self._bot_factory = bot_factory or Bot
        self._bots: dict[str, Bot] = {}
        self._lock = asyncio.Lock()
        self._next_index = 0

    def _ensure_bot(self, token: str) -> Bot:
        bot = self._bots.get(token)
        if bot is None:
            bot = self._bot_factory(token)
            self._bots[token] = bot
        return bot

    async def _next_token_order(self) -> list[str]:
        async with self._lock:
            start = self._next_index
            length = len(self._tokens)
            ordered = self._tokens[start:] + self._tokens[:start]
            self._next_index = (self._next_index + 1) % length
            return ordered

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> bool:
        """
        Try to send a Telegram message using each bot in rotation.

        Returns:
            True if a bot successfully sent the message, False otherwise.
        """
        queue = await self._next_token_order()
        
        success: bool = False
        for token in queue:
            bot = self._ensure_bot(token)
            try:
                _ = await bot.send_message(chat_id, text, **kwargs)
                success = True
            except (TelegramForbiddenError, TelegramBadRequest) as exc:
                logger.warning(
                    "Skipping token %s while sending notification: %s",
                    token,
                    exc,
                )
                continue
            except Exception as exc:  # pragma: no cover - fallback logging
                logger.error(
                    "Failed to send notification with token %s: %s",
                    token,
                    exc,
                    exc_info=True,
                )
                logger.error(
                    "Failed to send notification with token %s: %s",
                    token,
                    exc,
                    exc_info=True,
                )
        return success


_notification_sender: NotificationSender | None = None


def get_notification_sender() -> NotificationSender:
    """Get a shared NotificationSender instance."""
    global _notification_sender
    if _notification_sender is None:
        _notification_sender = NotificationSender(settings.TG_TOKENS_FOR_SENDING)
    return _notification_sender
