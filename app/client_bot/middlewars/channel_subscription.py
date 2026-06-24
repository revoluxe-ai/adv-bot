"""Middleware for checking support-channel subscription before bot usage.

This middleware sits after the invite gate and before the phone gate. It works
for messages and callback queries, blocks explicitly unsubscribed users, and
fails open when Telegram membership lookup is temporarily unavailable.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any, cast

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.const import SUPPORT_CHANNEL_ID
from app.client_bot.start_command import is_start_command_message
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.messages import NeedSubscribe
from app.core.redis_manager_v2.redis_client import RedisClient

logger = logging.getLogger(__name__)

ALLOWED_SUBSCRIPTION_STATUSES = {"member", "administrator", "creator"}
SUBSCRIPTION_CACHE_TTL_SECONDS = 60 * 60 * 24
SUBSCRIPTION_CACHE_PREFIX = "client_bot:support_channel_subscription"


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


def _build_subscription_cache_key(telegram_id: int) -> str:
    """Build the Redis key for positive channel-subscription cache."""
    return f"{SUBSCRIPTION_CACHE_PREFIX}:{telegram_id}"


@lru_cache(maxsize=1)
def _get_subscription_cache_client() -> RedisClient | None:
    """Return the shared Redis wrapper used for subscription cache.

    The helper is lazy and intentionally fail-open: if Redis wiring is not ready,
    the subscription check still works via Telegram API without local cache.
    """
    try:
        from app.core.di.app_container import AppContainer

        return AppContainer().redis_client_wrapper()
    except Exception:
        logger.warning(
            "Failed to initialize Redis client for support channel subscription cache",
            exc_info=True,
        )
        return None


async def _get_cached_subscription_status(telegram_id: int) -> bool | None:
    """Return cached positive subscription status if it exists."""
    redis_client = _get_subscription_cache_client()
    if redis_client is None:
        return None

    cached_value = await redis_client.get(_build_subscription_cache_key(telegram_id))
    if cached_value == "1":
        return True
    return None


async def _cache_positive_subscription_status(telegram_id: int) -> None:
    """Persist a positive subscription result for 24 hours."""
    redis_client = _get_subscription_cache_client()
    if redis_client is None:
        return

    await redis_client.set(
        _build_subscription_cache_key(telegram_id),
        "1",
        ex=SUBSCRIPTION_CACHE_TTL_SECONDS,
    )


async def is_user_subscribed_to_support_channel(
    bot: Bot,
    telegram_id: int,
) -> bool | None:
    """Return channel membership status with Redis cache and fail-open API handling."""
    cached_status = await _get_cached_subscription_status(telegram_id)
    if cached_status is True:
        return True

    try:
        member = await bot.get_chat_member(SUPPORT_CHANNEL_ID, telegram_id)
    except TelegramAPIError:
        logger.warning(
            "Failed to check support channel subscription for user %s",
            telegram_id,
            exc_info=True,
        )
        return None

    is_subscribed = getattr(member, "status", None) in ALLOWED_SUBSCRIPTION_STATUSES
    if is_subscribed:
        await _cache_positive_subscription_status(telegram_id)
    return is_subscribed


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
        logger.debug(
            "ChannelSubscriptionMiddleware: enter type=%s user=%s callback=%r text=%r",
            type(event).__name__,
            telegram_id,
            getattr(event, "data", None),
            getattr(event, "text", None),
        )
        if telegram_id is None:
            logger.debug("ChannelSubscriptionMiddleware: no telegram_id, pass through")
            return await handler(event, data)

        if is_bot_admin(telegram_id) or _is_whitelisted_event(event):
            logger.debug(
                "ChannelSubscriptionMiddleware: bypass user=%s admin=%s whitelisted=%s",
                telegram_id,
                is_bot_admin(telegram_id),
                _is_whitelisted_event(event),
            )
            return await handler(event, data)

        bot = data.get("bot")
        if not hasattr(bot, "get_chat_member") or not hasattr(bot, "send_message"):
            logger.debug("ChannelSubscriptionMiddleware: bot missing methods, pass through user=%s", telegram_id)
            return await handler(event, data)

        is_subscribed = await is_user_subscribed_to_support_channel(bot, telegram_id)
        logger.debug(
            "ChannelSubscriptionMiddleware: subscription result user=%s subscribed=%s",
            telegram_id,
            is_subscribed,
        )
        if is_subscribed is None or is_subscribed is True:
            return await handler(event, data)

        logger.debug("ChannelSubscriptionMiddleware: blocking user=%s", telegram_id)
        await send_need_subscribe_message(bot, event)
        return None
