"""Unit tests for support-channel subscription middleware and callback flow."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat, Message

from app.client_bot.const import ADMINS, SUPPORT_CHANNEL_URL
from app.client_bot.global_router import global_router
from app.client_bot.middlewars.channel_subscription import (
    ChannelSubscriptionMiddleware,
    SUBSCRIPTION_CACHE_TTL_SECONDS,
    is_user_subscribed_to_support_channel,
)
from app.client_bot.user_interface.handlers.user_subscribe_on_channel import (
    check_subscribe,
)
from app.client_bot.user_interface.views import callbacks, keyboards
from app.client_bot.user_interface.views.messages.messages import NeedSubscribe
from tests.helpers.telegram_message_asserts import (
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


@pytest.fixture(autouse=True)
def reset_subscription_cache_client():
    """Reset memoized Redis client; stub DI so unit tests skip real Redis."""
    from app.client_bot.middlewars import channel_subscription

    channel_subscription._reset_subscription_cache_client()
    with patch(
        "app.core.di.app_container.AppContainer",
        side_effect=RuntimeError("subscription cache DI stubbed in unit tests"),
    ):
        yield
    channel_subscription._reset_subscription_cache_client()


def _make_message_event(telegram_id: int, text: str = "ping") -> MagicMock:
    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=telegram_id, username="u")
    event.chat = MagicMock(spec=Chat, id=telegram_id)
    event.text = text
    return event


def _make_callback_event(telegram_id: int, data: str) -> MagicMock:
    event = MagicMock(spec=CallbackQuery)
    event.from_user = MagicMock(id=telegram_id, username="u")
    event.data = data
    event.message = MagicMock(spec=Message)
    event.message.chat = MagicMock(spec=Chat, id=telegram_id)
    event.message.answer = AsyncMock()
    # Real callback messages expose `date`; replay serialization reads it.
    event.message.date = datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc)
    event.message.message_id = 55
    event.answer = AsyncMock()
    return event


def _make_orphan_callback_event(telegram_id: int, data: str) -> MagicMock:
    """CallbackQuery without message/chat (e.g. inline from deleted message)."""
    event = MagicMock(spec=CallbackQuery)
    event.from_user = MagicMock(id=telegram_id, username="u")
    event.data = data
    event.message = None
    event.answer = AsyncMock()
    return event


@pytest.mark.parametrize("status", ["member", "administrator", "creator"])
@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_subscribed_statuses(status: str) -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(111)
    handler = AsyncMock()
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status=status))

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


@pytest.mark.asyncio
async def test_channel_subscription_middleware_admits_from_positive_cache_without_telegram() -> None:
    """Hot path: positive Redis hit admits without get_chat_member (≤1h TTL)."""
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(110)
    handler = AsyncMock()
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status="left"))
    bot.send_message = AsyncMock()
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="1")

    with patch(
        "app.client_bot.middlewars.channel_subscription._get_subscription_cache_client",
        return_value=redis_client,
    ):
        await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})
    bot.get_chat_member.assert_not_awaited()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_subscribe_revalidates_telegram_and_rejects_stale_positive_cache() -> None:
    """CheckSubscribe must revalidate Telegram; stale Redis ``1`` must not confirm.

    Safer gate: after a positive cache hit, live unsubscribed/False must not
    answer «Подписка подтверждена» and must not continue the start/replay flow.
    """
    callback = _make_callback_event(112, callbacks.CheckSubscribe().pack())
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status="left"))
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="1")
    redis_client.delete = AsyncMock(return_value=1)

    with patch(
        "app.client_bot.middlewars.channel_subscription._get_subscription_cache_client",
        return_value=redis_client,
    ), patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.callback_start_registration",
        new=AsyncMock(),
    ) as start_mock:
        await check_subscribe(callback, bot, state)

    start_mock.assert_not_awaited()
    bot.get_chat_member.assert_awaited()
    callback.answer.assert_not_awaited()
    callback.message.answer.assert_not_awaited()
    bot.send_message.assert_awaited()


@pytest.mark.parametrize("status", ["left", "kicked", "restricted", "unknown"])
@pytest.mark.asyncio
async def test_channel_subscription_middleware_blocks_unsubscribed_statuses(
    status: str,
) -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(222)
    handler = AsyncMock()
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status=status))
    bot.send_message = AsyncMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.call_args.kwargs
    text = kwargs["text"]
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "функций",
            "подписаны",
            "канал",
            "Подпишитесь",
            "Проверить подписку",
            "доступ к функциям",
        ],
    )
    assert_no_raw_technical_text(text)
    assert_keyboard_has_buttons(kwargs["reply_markup"], ["Подписаться", "Проверить подписку"])


@pytest.mark.asyncio
async def test_channel_subscription_middleware_stores_pending_callback_when_blocked() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_callback_event(223, "adv:test")
    handler = AsyncMock()
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status="left"))
    bot.send_message = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    state.update_data = AsyncMock()

    await middleware(handler, event, {"bot": bot, "state": state})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    state.update_data.assert_awaited_once()
    saved_payload = state.update_data.await_args.kwargs["pending_subscription_callback"]
    assert '"data": "adv:test"' in saved_payload


@pytest.mark.asyncio
async def test_channel_subscription_middleware_blocks_orphan_callback_with_need_subscribe() -> None:
    """Orphan CallbackQuery (no message/chat) still gets NeedSubscribe via user id."""
    middleware = ChannelSubscriptionMiddleware()
    event = _make_orphan_callback_event(224, "adv:test")
    handler = AsyncMock()
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status="left"))
    bot.send_message = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    state.update_data = AsyncMock()

    await middleware(handler, event, {"bot": bot, "state": state})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.kwargs["chat_id"] == 224
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_channel_subscription_middleware_orphan_callback_fail_closed_on_telegram_error() -> None:
    """Orphan CallbackQuery with lookup failure still gets unavailable screen."""
    middleware = ChannelSubscriptionMiddleware()
    event = _make_orphan_callback_event(225, "adv:test")
    handler = AsyncMock()
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with patch(
        "app.client_bot.middlewars.channel_subscription.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=None),
    ):
        await middleware(handler, event, {"bot": bot})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.kwargs["chat_id"] == 225
    text = bot.send_message.call_args.kwargs["text"]
    assert "не удалось проверить" in text


@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_start_command() -> None:
    """``/start`` whitelisted: onboarding hook before subscription gate (by design)."""
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(333, "/start")
    handler = AsyncMock()
    bot = MagicMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})
    assert not hasattr(bot, "get_chat_member") or bot.get_chat_member.called is False


@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_check_subscribe_callback() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_callback_event(444, callbacks.CheckSubscribe().pack())
    handler = AsyncMock()
    bot = MagicMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_gate_callback_before_subscription() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_callback_event(445, callbacks.Gate(action="invite_enter").pack())
    handler = AsyncMock()
    bot = MagicMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_gate_invite_state_message() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(446, "INVITE-CODE")
    handler = AsyncMock()
    bot = MagicMock()
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value="GateInvite:waiting_code")

    await middleware(handler, event, {"bot": bot, "state": state})

    handler.assert_awaited_once_with(event, {"bot": bot, "state": state})


@pytest.mark.asyncio
async def test_channel_subscription_middleware_admin_bypass() -> None:
    if not ADMINS:
        pytest.skip("ADMINS empty")

    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(ADMINS[0])
    handler = AsyncMock()
    bot = MagicMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


@pytest.mark.asyncio
async def test_channel_subscription_middleware_fail_closed_on_telegram_error() -> None:
    """Lookup uncertainty blocks access but uses a distinct error screen."""
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(555)
    handler = AsyncMock()
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with patch(
        "app.client_bot.middlewars.channel_subscription.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=None),
    ):
        await middleware(handler, event, {"bot": bot})

    handler.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    text = bot.send_message.call_args.kwargs["text"]
    assert "не удалось проверить" in text
    assert "вы должны быть подписаны" not in text


@pytest.mark.asyncio
async def test_subscription_lookup_logs_telegram_error_at_error_level(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Telegram lookup outages are ERROR-visible and return fail-closed ``None``."""
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(
        side_effect=TelegramAPIError(
            method="getChatMember",
            message="temporary Telegram failure",
        )
    )

    with caplog.at_level(
        logging.ERROR,
        logger="app.client_bot.middlewars.channel_subscription",
    ):
        result = await is_user_subscribed_to_support_channel(bot, 556)

    assert result is None
    assert "Support channel subscription check failed" in caplog.text
    assert "user_id=556" in caplog.text


@pytest.mark.asyncio
async def test_channel_subscription_middleware_caches_positive_status_for_hour() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(556)
    handler = AsyncMock()
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status="member"))
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=None)
    redis_client.set = AsyncMock(return_value=True)

    with patch(
        "app.client_bot.middlewars.channel_subscription._get_subscription_cache_client",
        return_value=redis_client,
    ):
        await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})
    redis_client.set.assert_awaited_once_with(
        "client_bot:support_channel_subscription:556",
        "1",
        ex=SUBSCRIPTION_CACHE_TTL_SECONDS,
    )


def test_get_subscription_cache_client_retries_after_failed_init() -> None:
    """Failed DI/Redis init must not stick: next call can recover a client."""
    from app.client_bot.middlewars import channel_subscription

    channel_subscription._reset_subscription_cache_client()
    redis_client = MagicMock()
    container_ok = MagicMock()
    container_ok.redis_client_wrapper.return_value = redis_client

    with patch(
        "app.core.di.app_container.AppContainer",
        side_effect=[RuntimeError("DI not ready"), container_ok],
    ):
        assert channel_subscription._get_subscription_cache_client() is None
        assert channel_subscription._get_subscription_cache_client() is redis_client
        # Third call uses memoized success — AppContainer not called again.
        assert channel_subscription._get_subscription_cache_client() is redis_client

    channel_subscription._reset_subscription_cache_client()


@pytest.mark.asyncio
async def test_check_subscribe_handler_returns_to_start_flow_when_subscribed() -> None:
    callback = _make_callback_event(666, callbacks.CheckSubscribe().pack())
    bot = MagicMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.callback_start_registration",
        new=AsyncMock(),
    ) as start_mock:
        await check_subscribe(callback, bot, state)

    callback.answer.assert_not_awaited()
    callback.message.answer.assert_not_awaited()
    start_mock.assert_awaited_once_with(callback, bot, state)
    state.update_data.assert_awaited_once_with(pending_subscription_callback=None)


@pytest.mark.asyncio
async def test_check_subscribe_handler_replays_pending_callback_when_subscribed() -> None:
    callback = _make_callback_event(667, callbacks.CheckSubscribe().pack())
    callback.message.message_id = 99
    bot = MagicMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={"pending_subscription_callback": '{"id":"cb","data":"adv:test"}'}
    )
    state.update_data = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.replay_serialized_callback",
        new=AsyncMock(),
    ) as replay_mock, patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.callback_start_registration",
        new=AsyncMock(),
    ) as start_mock:
        await check_subscribe(callback, bot, state)

    callback.answer.assert_not_awaited()
    callback.message.answer.assert_not_awaited()
    replay_mock.assert_awaited_once_with(
        bot,
        '{"id":"cb","data":"adv:test"}',
    )
    start_mock.assert_not_awaited()
    state.update_data.assert_awaited_once_with(pending_subscription_callback=None)


@pytest.mark.asyncio
async def test_check_subscribe_handler_repeats_need_subscribe_when_not_subscribed() -> None:
    callback = _make_callback_event(777, callbacks.CheckSubscribe().pack())
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()

    with patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=False),
    ):
        await check_subscribe(callback, bot, state)

    callback.answer.assert_not_awaited()
    callback.message.answer.assert_not_awaited()
    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_subscribe_handler_fail_closed_on_telegram_error() -> None:
    """CheckSubscribe must not treat None as confirmed subscription."""
    callback = _make_callback_event(778, callbacks.CheckSubscribe().pack())
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.callback_start_registration",
        new=AsyncMock(),
    ) as start_mock:
        await check_subscribe(callback, bot, state)

    start_mock.assert_not_awaited()
    callback.answer.assert_not_awaited()
    callback.message.answer.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    state.update_data.assert_not_awaited()


def test_subscribe_keyboard_has_url_and_recheck_buttons() -> None:
    keyboard = keyboards.get_subscribe_keyboard()
    assert_keyboard_has_buttons(keyboard, ["Подписаться", "Проверить подписку"])
    assert keyboard.inline_keyboard[0][0].url == SUPPORT_CHANNEL_URL
    assert keyboard.inline_keyboard[1][0].callback_data == callbacks.CheckSubscribe().pack()


def test_need_subscribe_message_text_is_user_facing() -> None:
    text = NeedSubscribe(bot=MagicMock(), chat_id=1).text
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "функций",
            "подписаны",
            "канал",
            "Подпишитесь",
            "Проверить подписку",
            "доступ к функциям",
        ],
    )
    assert_no_raw_technical_text(text)


def test_global_router_middleware_registration_for_gate_channel_phone_onion() -> None:
    """Registration list is reversed at runtime: Gate → Channel → Phone.

    Aiogram ``wrap_middlewares`` iterates ``reversed(middlewares)``, so the
    last registered middleware is outermost and runs first.
    """
    message_middlewares = [
        middleware.__class__.__name__
        for middleware in global_router.message.middleware._middlewares
    ]
    callback_middlewares = [
        middleware.__class__.__name__
        for middleware in global_router.callback_query.middleware._middlewares
    ]

    assert message_middlewares == [
        "ReturnToStart",
        "PhoneRequiredMiddleware",
        "ChannelSubscriptionMiddleware",
        "GateMiddleware",
    ]
    assert callback_middlewares == [
        "PhoneRequiredMiddleware",
        "ChannelSubscriptionMiddleware",
        "GateMiddleware",
    ]
