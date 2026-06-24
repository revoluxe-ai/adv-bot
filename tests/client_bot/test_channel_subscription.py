"""Unit tests for support-channel subscription middleware and callback flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message

from app.client_bot.const import ADMINS, SUPPORT_CHANNEL_URL
from app.client_bot.global_router import global_router
from app.client_bot.middlewars.channel_subscription import (
    ChannelSubscriptionMiddleware,
)
from app.client_bot.user_interface.handlers.user_subscribe_on_channel import (
    check_subscribe,
)
from app.client_bot.user_interface.views import callbacks, keyboards


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
    event.answer = AsyncMock()
    return event


@pytest.mark.parametrize("status", ["member", "administrator", "creator"])
@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_subscribed_statuses(
    status: str,
) -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(111)
    handler = AsyncMock()
    bot = MagicMock()
    bot.get_chat_member = AsyncMock(return_value=MagicMock(status=status))

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


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


@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_start_command() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(333, "/start")
    handler = AsyncMock()
    bot = MagicMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})
    assert bot.get_chat_member.called is False if hasattr(bot, "get_chat_member") else True


@pytest.mark.asyncio
async def test_channel_subscription_middleware_allows_check_subscribe_callback() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_callback_event(444, callbacks.CheckSubscribe().pack())
    handler = AsyncMock()
    bot = MagicMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


@pytest.mark.asyncio
async def test_channel_subscription_middleware_admin_bypass() -> None:
    if not ADMINS:
        pytest.skip("ADMINS пустой")

    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(ADMINS[0])
    handler = AsyncMock()
    bot = MagicMock()

    await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


@pytest.mark.asyncio
async def test_channel_subscription_middleware_fail_open_on_telegram_error() -> None:
    middleware = ChannelSubscriptionMiddleware()
    event = _make_message_event(555)
    handler = AsyncMock()
    bot = MagicMock()

    with patch(
        "app.client_bot.middlewars.channel_subscription.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=None),
    ):
        await middleware(handler, event, {"bot": bot})

    handler.assert_awaited_once_with(event, {"bot": bot})


@pytest.mark.asyncio
async def test_check_subscribe_handler_returns_to_start_flow_when_subscribed() -> None:
    callback = _make_callback_event(666, callbacks.CheckSubscribe().pack())
    bot = MagicMock()
    state = MagicMock()

    with patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.is_user_subscribed_to_support_channel",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.client_bot.user_interface.handlers.user_subscribe_on_channel.callback_start_registration",
        new=AsyncMock(),
    ) as start_mock:
        await check_subscribe(callback, bot, state)

    callback.answer.assert_awaited_once_with("Подписка подтверждена")
    start_mock.assert_awaited_once_with(callback, bot, state)


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

    callback.answer.assert_awaited_once()
    bot.send_message.assert_awaited_once()


def test_subscribe_keyboard_has_url_and_recheck_buttons() -> None:
    keyboard = keyboards.get_subscribe_keyboard()

    assert keyboard.inline_keyboard[0][0].text == "Подписаться"
    assert keyboard.inline_keyboard[0][0].url == SUPPORT_CHANNEL_URL
    assert keyboard.inline_keyboard[1][0].text == "Проверить подписку"
    assert (
        keyboard.inline_keyboard[1][0].callback_data
        == callbacks.CheckSubscribe().pack()
    )


def test_global_router_contains_channel_subscription_before_phone_required() -> None:
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
        "GateMiddleware",
        "ChannelSubscriptionMiddleware",
        "PhoneRequiredMiddleware",
    ]
    assert callback_middlewares == [
        "GateMiddleware",
        "ChannelSubscriptionMiddleware",
        "PhoneRequiredMiddleware",
    ]
