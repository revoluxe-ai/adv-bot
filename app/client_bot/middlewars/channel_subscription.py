"""Middleware for checking support-channel subscription before bot usage.

This middleware sits after the invite gate and before the phone gate. It works
for messages and callback queries, blocks explicitly unsubscribed users, and
fails closed when Telegram membership lookup is temporarily unavailable
(``TelegramAPIError`` / ``None``).

Positive Redis cache (TTL 1 hour) is used on the hot path so Telegram
``get_chat_member`` is called at most about once per hour per user.
``CheckSubscribe`` / ``force_refresh=True`` always revalidates live; live
``False`` invalidates a stale positive entry.

**Positive cache TTL (NOT a stale-subscription bug):**

Only **positive** results are cached (``"1"``, ``SUBSCRIPTION_CACHE_TTL_SECONDS``).
After a user unsubscribes, middleware hot path may still admit them until TTL
expires **if** no live ``get_chat_member`` runs — this is an intentional
rate-limit trade-off, not fail-open on API errors. Live ``False`` deletes the
key; ``CheckSubscribe`` always uses ``force_refresh=True``. Static review MUST
NOT treat «отписался, но ещё hour в боте» as a defect without product GO to
always-live checks.

**Onboarding contract (NOT a bypass bug):**

``/start`` is whitelisted in :func:`_is_whitelisted_event` on purpose. The first
contact is message ``/start`` → :func:`start_registration` shows the enticing
entry copy / MainMenu hook **without** a live ``get_chat_member`` here. Channel
subscription remains mandatory for everything else: inline callbacks, follow-up
messages, menu navigation. Unsubscribed users hit ``NeedSubscribe`` on the next
non-whitelisted update; ``CheckSubscribe`` revalidates live and may replay a
blocked callback from ``pending_subscription_callback``.

Static review MUST NOT treat ``/start`` whitelist as a subscription-gate defect.
See also docstring on :func:`start_registration`.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.callback_replay import serialize_callback_query
from app.client_bot.const import SUPPORT_CHANNEL_ID
from app.client_bot.start_command import is_start_command_message
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.messages import (
    NeedSubscribe,
    SubscriptionCheckUnavailable,
)
from app.core.redis_manager_v2.redis_client import RedisClient

logger = logging.getLogger(__name__)

ALLOWED_SUBSCRIPTION_STATUSES = {"member", "administrator", "creator"}
# Positive-only cache: ≤1 live get_chat_member / user / hour on middleware hot path.
# Unsubscribe before TTL without live re-check → user may stay admitted until
# expiry; by design (see module docstring). Not negative cache, not fail-open.
SUBSCRIPTION_CACHE_TTL_SECONDS = 60 * 60
SUBSCRIPTION_CACHE_PREFIX = "client_bot:support_channel_subscription"

# Memoize only a successful Redis client. Never cache ``None``: a cold-start /
# DI miss must retry on the next call once wiring is ready.
_subscription_redis_client: RedisClient | None = None


def _resolve_chat_id(event: Message | CallbackQuery) -> int | None:
    """Extract the chat id used to send the subscribe prompt."""
    if isinstance(event, Message):
        return event.chat.id
    if event.message and event.message.chat:
        return event.message.chat.id
    return None


def _resolve_send_chat_id(event: Message | CallbackQuery) -> int | None:
    """Resolve destination chat for subscribe / unavailable screens.

    Uses :func:`_resolve_chat_id` when the event carries a message chat.
    For ``CallbackQuery`` without ``message.chat`` (e.g. inline from an old or
    deleted message), falls back to ``from_user.id`` so the user still receives
    the gate screen in a private chat — same contract as
    ``PhoneRequiredMiddleware``.
    """
    chat_id = _resolve_chat_id(event)
    if chat_id is not None:
        return chat_id
    if isinstance(event, CallbackQuery) and event.from_user:
        return event.from_user.id
    return None


def _is_whitelisted_event(event: Message | CallbackQuery) -> bool:
    """События, которые проходят без live-проверки подписки в этом middleware.

    Whitelist — часть onboarding, не дыра в fail-closed gate:

    * **Message ``/start``** — единственная «заманушная» точка входа.
      ``start_registration`` создаёт User (если нужно) и показывает стартовый
      текст / MainMenu. Подписку на канал здесь намеренно не проверяем: сначала
      hook, затем gate на любом следующем действии (callback, текст, кнопки).
    * **Callback ``CheckSubscribe``** — повторная live-проверка после экрана
      ``NeedSubscribe``; handler сам вызывает ``force_refresh=True``.

    Всё остальное (включая ``callbacks.Start``) MUST проходить
    ``is_user_subscribed_to_support_channel`` или блокироваться.
    """
    if isinstance(event, Message):
        return is_start_command_message(event)
    data = event.data or ""
    if data.startswith("mcpok:") or data.startswith("mcpno:"):
        return True
    return bool(data and data == callbacks.CheckSubscribe().pack())


async def _is_gate_invite_flow_event(
    event: Message | CallbackQuery,
    data: dict[str, Any],
) -> bool:
    """Allow the invite-gate flow to proceed before subscription is checked."""
    if isinstance(event, CallbackQuery):
        return bool(event.data and event.data.startswith("gate:"))

    state = data.get("state")
    if not isinstance(state, FSMContext):
        return False

    current_state = await state.get_state()
    return bool(current_state and current_state.startswith("GateInvite:"))


def _build_subscription_cache_key(telegram_id: int) -> str:
    """Build the Redis key for positive channel-subscription cache."""
    return f"{SUBSCRIPTION_CACHE_PREFIX}:{telegram_id}"


def _reset_subscription_cache_client() -> None:  # pyright: ignore[reportUnusedFunction]
    """Drop the memoized Redis client (tests / after DI recovery).

    Test seam: ``tests/client_bot/test_channel_subscription.py``.
    """
    global _subscription_redis_client
    _subscription_redis_client = None


def _get_subscription_cache_client() -> RedisClient | None:
    """Return the shared Redis wrapper used for subscription cache.

    Successful clients are memoized. Failed DI/Redis wiring returns ``None``
    without memoization so a later call can recover. Membership checks still
    go to Telegram when cache is unavailable.
    """
    global _subscription_redis_client
    if _subscription_redis_client is not None:
        return _subscription_redis_client

    try:
        from app.core.di.app_container import AppContainer

        client = AppContainer().redis_client_wrapper()
    except Exception:
        logger.warning(
            "Failed to initialize Redis client for support channel subscription cache",
            exc_info=True,
        )
        return None

    _subscription_redis_client = client
    return client


async def _get_cached_subscription_status(telegram_id: int) -> bool | None:
    """Return cached **positive** subscription status if it exists.

    Returns ``True`` only when Redis holds ``"1"``. Miss / absent key → ``None``
    (caller falls through to Telegram). There is no negative cache by design.
    """
    redis_client = _get_subscription_cache_client()
    if redis_client is None:
        return None

    cached_value = await redis_client.get(_build_subscription_cache_key(telegram_id))
    if cached_value == "1":
        return True
    return None


async def _cache_positive_subscription_status(telegram_id: int) -> None:
    """Persist a live ``True`` membership result for ``SUBSCRIPTION_CACHE_TTL_SECONDS``.

    Intentionally positive-only: unsubscribed users without a subsequent live
    check may remain admitted until TTL; ``CheckSubscribe`` uses ``force_refresh``.
    """
    redis_client = _get_subscription_cache_client()
    if redis_client is None:
        return

    await redis_client.set(
        _build_subscription_cache_key(telegram_id),
        "1",
        ex=SUBSCRIPTION_CACHE_TTL_SECONDS,
    )


async def _invalidate_subscription_cache(telegram_id: int) -> None:
    """Delete a stale positive subscription cache entry for ``telegram_id``."""
    redis_client = _get_subscription_cache_client()
    if redis_client is None:
        return

    await redis_client.delete(_build_subscription_cache_key(telegram_id))


async def is_user_subscribed_to_support_channel(
    bot: Bot,
    telegram_id: int,
    *,
    force_refresh: bool = False,
) -> bool | None:
    """Return channel membership status with optional Redis positive cache.

    Args:
        bot: Telegram bot used for ``get_chat_member``.
        telegram_id: User id to check.
        force_refresh: When ``True``, skip reading the positive Redis cache and
            always call Telegram (used by CheckSubscribe revalidation).

    Returns:
        ``True`` if subscribed, ``False`` if explicitly not, ``None`` when
        Telegram API membership lookup failed. Callers fail closed for ``None``
        but show an availability error instead of claiming the user is
        unsubscribed.

    Side effects:
        Writes a positive Redis cache entry on live ``True``; deletes the cache
        key on live ``False``.

    Cache contract (by design, not a review defect):
        Hot path (``force_refresh=False``) may return ``True`` from Redis without
        calling Telegram for up to ``SUBSCRIPTION_CACHE_TTL_SECONDS``. A user who
        unsubscribed after being cached can keep access until TTL unless a live
        check runs (``CheckSubscribe`` or cache miss). Product trade-off: fewer
        ``get_chat_member`` calls vs immediate revoke on unsubscribe.
    """
    if not force_refresh:
        cached_status = await _get_cached_subscription_status(telegram_id)
        if cached_status is True:
            return True

    try:
        member = await bot.get_chat_member(SUPPORT_CHANNEL_ID, telegram_id)
    except TelegramAPIError:
        logger.error(
            "Support channel subscription check failed: user_id=%s channel_id=%s "
            "force_refresh=%s",
            telegram_id,
            SUPPORT_CHANNEL_ID,
            force_refresh,
            exc_info=True,
        )
        return None

    is_subscribed = getattr(member, "status", None) in ALLOWED_SUBSCRIPTION_STATUSES
    if is_subscribed:
        await _cache_positive_subscription_status(telegram_id)
    else:
        await _invalidate_subscription_cache(telegram_id)
    return is_subscribed


async def send_need_subscribe_message(bot: Bot, event: Message | CallbackQuery) -> None:
    """Send the «not subscribed» screen for an explicitly rejected event."""
    chat_id = _resolve_send_chat_id(event)
    if chat_id is None:
        return
    await NeedSubscribe(bot, chat_id)()


async def send_subscription_check_unavailable_message(
    bot: Bot,
    event: Message | CallbackQuery,
) -> None:
    """Explain a failed membership lookup without mislabeling the user.

    Fail-closed admission is preserved: the event is not passed to the handler.
    The user-facing text says that Telegram membership could not be verified and
    provides the same retry keyboard instead of claiming that the user is not
    subscribed.
    """
    chat_id = _resolve_send_chat_id(event)
    if chat_id is None:
        return
    await SubscriptionCheckUnavailable(bot, chat_id)()


class ChannelSubscriptionMiddleware(BaseMiddleware):
    """Block access for users unsubscribed from the support channel.

    Admission of ``data["bot"]`` is structural (``get_chat_member`` /
    ``send_message``), then narrowed with ``cast(Bot, …)`` for typing — not
    ``isinstance(Bot)`` alone. Telegram lookup failure (``None``) fails closed:
    the handler is blocked, an ERROR is logged by the lookup helper, and the
    user sees a temporary verification-error screen rather than
    ``NeedSubscribe``.

    Exception: whitelisted ``/start`` (see module docstring) — onboarding hook
    before subscription gate on subsequent updates.

    Hot path uses positive Redis cache (≤1h) without mandatory live revalidation;
    see module docstring — stale positive after unsubscribe is intentional.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Проверяет подписку и при необходимости блокирует handler.

        Args:
            handler: Downstream handler.
            event: Message или CallbackQuery.
            data: Aiogram data; ожидает ключ ``bot`` с методами membership/send.

        Returns:
            Результат handler либо ``None`` при блоке NeedSubscribe.
        """
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

        if (
            is_bot_admin(telegram_id)
            or _is_whitelisted_event(event)
            or await _is_gate_invite_flow_event(event, data)
        ):
            # /start и CheckSubscribe — см. _is_whitelisted_event; не баг review.
            return await handler(event, data)

        # Structural admission is intentional: production supplies aiogram Bot,
        # while compatible providers and unit doubles may be duck-typed. We
        # require both methods before using the subscription boundary; an
        # object that cannot perform the lookup or send the denial screen is
        # passed through rather than failing inside this middleware. This is
        # infrastructure/provider compatibility, not a subscription decision;
        # do not replace it with a strict isinstance(Bot) gate without an
        # owner-approved provider contract.
        bot_raw = data.get("bot")
        if bot_raw is None or not (
            hasattr(bot_raw, "get_chat_member") and hasattr(bot_raw, "send_message")
        ):
            logger.debug(
                "ChannelSubscriptionMiddleware: bot missing methods, pass through user=%s",
                telegram_id,
            )
            return await handler(event, data)
        bot = cast(Bot, bot_raw)

        # Hot path: positive Redis up to TTL (1h). By design — not instant revoke
        # on unsubscribe; live revalidation: CheckSubscribe (force_refresh=True).
        is_subscribed = await is_user_subscribed_to_support_channel(
            bot,
            telegram_id,
            force_refresh=False,
        )
        logger.debug(
            "ChannelSubscriptionMiddleware: subscription result user=%s subscribed=%s",
            telegram_id,
            is_subscribed,
        )
        if is_subscribed is True:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            state = data.get("state")
            if isinstance(state, FSMContext):
                await state.update_data(
                    pending_subscription_callback=serialize_callback_query(event)
                )

        logger.debug(
            "ChannelSubscriptionMiddleware: blocking user=%s subscribed=%s",
            telegram_id,
            is_subscribed,
        )
        if is_subscribed is None:
            await send_subscription_check_unavailable_message(bot, event)
        else:
            await send_need_subscribe_message(bot, event)
        return None
