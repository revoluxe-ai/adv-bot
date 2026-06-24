"""Middleware for checking support-channel subscription before bot usage.

This middleware sits after the invite gate and before the phone gate. It works
for messages and callback queries, blocks explicitly unsubscribed users, and
fails open when Telegram membership lookup is temporarily unavailable.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.const import SUPPORT_CHANNEL_ID
from app.client_bot.start_command import is_start_command_message
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.messages import NeedSubscribe

logger = logging.getLogger(__name__)

ALLOWED_SUBSCRIPTION_STATUSES = {"member", "administrator", "creator"}


def _resolve_chat_id(event: Message | CallbackQuery) -> int | None:
    """Extract the chat id used to send the subscribe prompt."""
    if isinstance(event, Message):
        return event.chat.id
    if event.message and event.message.chat:
        return event.message.chat.id
    return None


def _is_whitelisted_event(event: Message | CallbackQuery) -> bool:
    """Allow `/start` and the explicit subscription re-check callback."""
    if isinstance(event, Message):
        return is_start_command_message(event)
    return bool(event.data and event.data == callbacks.CheckSubscribe().pack())


async def is_user_subscribed_to_support_channel(
    bot: Bot,
    telegram_id: int,
) -> bool | None:
    """Return channel membership status with fail-open API error handling."""
    try:
        member = await bot.get_chat_member(SUPPORT_CHANNEL_ID, telegram_id)
    except TelegramAPIError:
        logger.warning(
            "Failed to check support channel subscription for user %s",
            telegram_id,
            exc_info=True,
        )
        return None

    return getattr(member, "status", None) in ALLOWED_SUBSCRIPTION_STATUSES


async def send_need_subscribe_message(bot: Bot, event: Message | CallbackQuery) -> None:
    """Send the existing NeedSubscribe screen for a blocked event."""
    chat_id = _resolve_chat_id(event)
    if chat_id is None:
        return
    await NeedSubscribe(bot, chat_id)()


class ChannelSubscriptionMiddleware(BaseMiddleware):
    """Block access for users unsubscribed from the support channel."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event = cast(Message | CallbackQuery, event)
        telegram_id = event.from_user.id if event.from_user else None
        if telegram_id is None:
            return await handler(event, data)

        if is_bot_admin(telegram_id) or _is_whitelisted_event(event):
            return await handler(event, data)

        bot = data.get("bot")
        if not hasattr(bot, "get_chat_member") or not hasattr(bot, "send_message"):
            return await handler(event, data)

        is_subscribed = await is_user_subscribed_to_support_channel(bot, telegram_id)
        if is_subscribed is None or is_subscribed is True:
            return await handler(event, data)

        await send_need_subscribe_message(bot, event)
        return None
