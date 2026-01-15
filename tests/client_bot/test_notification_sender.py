import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from unittest.mock import AsyncMock, MagicMock

from app.client_bot.notification_sender import NotificationSender


def _make_bot_factory(created_bots: list[MagicMock]):
    def factory(token: str):
        bot = MagicMock()
        bot.token = token
        bot.send_message = AsyncMock(return_value=None)
        created_bots.append(bot)
        return bot

    return factory


@pytest.mark.asyncio
async def test_send_message_success_on_first_token():
    tokens = ["t1", "t2"]
    bots: list[MagicMock] = []
    sender = NotificationSender(tokens, bot_factory=_make_bot_factory(bots))

    result = await sender.send_message(chat_id=1, text="hello")

    assert result is True
    assert bots[0].send_message.await_count == 1
    assert len(bots) == 1


@pytest.mark.asyncio
async def test_send_message_skips_forbidden_tokens():
    tokens = ["first", "second"]
    bots: list[MagicMock] = []

    def factory(token: str):
        bot = MagicMock()
        bot.token = token
        bot.send_message = AsyncMock(return_value=None)
        if token == "first":
            bot.send_message.side_effect = TelegramForbiddenError(
                message="blocked", method="test"
            )
        bots.append(bot)
        return bot

    sender = NotificationSender(tokens, bot_factory=factory)

    success = await sender.send_message(chat_id=42, text="hi")

    assert success is True
    assert bots[0].send_message.await_count == 1
    assert bots[1].send_message.await_count == 1


@pytest.mark.asyncio
async def test_send_message_returns_false_when_all_tokens_fail():
    tokens = ["one", "two"]
    bots: list[MagicMock] = []

    def factory(token: str):
        bot = MagicMock()
        bot.token = token
        bot.send_message = AsyncMock(
            side_effect=TelegramBadRequest(message="chat not found", method="send")
        )
        bots.append(bot)
        return bot

    sender = NotificationSender(tokens, bot_factory=factory)

    success = await sender.send_message(chat_id=99, text="alert")

    assert success is False
    assert bots[0].send_message.await_count == 1
    assert bots[1].send_message.await_count == 1
