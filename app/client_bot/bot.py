from __future__ import annotations

from collections.abc import Sequence

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from app.settings import settings

_ = load_dotenv()

__all__ = [
    "aclose_telegram_http_session",
    "create_bot_for_token",
    "get_bot",
    "get_bots_for_tokens",
]

_telegram_http_session: AiohttpSession | None = None
_bots_by_token: dict[str, Bot] = {}


def _get_telegram_http_session() -> AiohttpSession:
    global _telegram_http_session
    if _telegram_http_session is None:
        # Long poll + proxy: need generous timeouts (default is too tight for slow tunnels).
        _telegram_http_session = AiohttpSession(
            proxy=settings.PROXY,
            timeout=120,
        )
    return _telegram_http_session


def create_bot_for_token(token: str) -> Bot:
    if token in _bots_by_token:
        return _bots_by_token[token]
    bot = Bot(token=token, session=_get_telegram_http_session())
    _bots_by_token[token] = bot
    return bot


def get_bot() -> Bot:
    return create_bot_for_token(settings.TELEGRAM_BOT_TOKEN)


def get_bots_for_tokens(tokens: Sequence[str]) -> list[Bot]:
    return [create_bot_for_token(t) for t in tokens]


async def aclose_telegram_http_session() -> None:
    global _telegram_http_session
    if _telegram_http_session is not None:
        await _telegram_http_session.close()
        _telegram_http_session = None
    _bots_by_token.clear()
    from app.client_bot.notification_sender import reset_notification_sender

    reset_notification_sender()
