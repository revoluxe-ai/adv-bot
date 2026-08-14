"""Invite-gate middleware for users without ``User.passed_gate``."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.start_command import is_start_command_message
from app.client_bot.user_interface.views.gate import (
    get_gate_keyboard,
    get_gate_message_text,
)
from app.client_bot.utils import create_user
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker
logger = logging.getLogger(__name__)


def _resolve_chat_id(event: Message | CallbackQuery) -> int | None:
    """Extract the destination chat id for a gate reply."""
    if isinstance(event, Message):
        return event.chat.id
    if event.message and event.message.chat:
        return event.message.chat.id
    return None


async def resolve_user_in_session(
    session: AsyncSession,
    event: Message | CallbackQuery,
    telegram_id: int,
) -> User:
    """Load or create the gate user within an existing WRITE session.

    Caller opens ``sm(read_only=False)`` and passes the session here.
    Creation delegates to :func:`create_user` with the injected session.
    """
    stmt = select(User).options(load_only(User.passed_gate)).where(
        User.user_telegram_id == telegram_id
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    chat_id = _resolve_chat_id(event)
    user = await create_user(
        session,
        telegram_id,
        username=event.from_user.username if event.from_user else None,
        adv_updater_user_chat_id=chat_id,
    )
    logger.debug(
        "GateMiddleware: created user=%s chat_id=%s",
        telegram_id,
        chat_id,
    )
    return user


async def _resolve_user(event: Message | CallbackQuery, telegram_id: int) -> User:
    """Load the current user, creating a minimal record when needed.

    Parent WRITE seam: ``sm(read_only=False)`` → :func:`resolve_user_in_session`.
    """
    async with _sm(read_only=False) as session:
        return await resolve_user_in_session(session, event, telegram_id)


async def _message_state_name(data: dict[str, Any]) -> str | None:
    """Return the current FSM state name when available."""
    state = data.get("state")
    if state is None:
        return None
    current = await state.get_state()
    return str(current) if current is not None else None


async def _is_presentation_only_allowed(
    event: Message | CallbackQuery,
    data: dict[str, Any],
) -> bool:
    """Whitelist the reduced presentation-only onboarding flow."""
    if isinstance(event, Message):
        if is_start_command_message(event):
            return True
        state_name = await _message_state_name(data)
        return bool(
            state_name
            and (
                state_name.startswith("PresentationRequest:")
                or state_name.startswith("GateInvite:")
            )
        )

    return bool(
        event.data
        and (
            event.data.startswith("presentation:")
            or event.data.startswith("gate:")
        )
    )


async def _is_regular_gate_allowed(
    event: Message | CallbackQuery,
    data: dict[str, Any],
) -> bool:
    """Whitelist classic invite-gate entry points before passed_gate."""
    if isinstance(event, CallbackQuery):
        return bool(event.data and event.data.startswith("gate:"))

    if getattr(event, "successful_payment", None) is not None:
        return True

    state_name = await _message_state_name(data)
    return bool(state_name and state_name.startswith("GateInvite:"))


class GateMiddleware(BaseMiddleware):
    """Block non-whitelisted access until the user passes the invite gate."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event = cast(Message | CallbackQuery, event)
        telegram_id = event.from_user.id if event.from_user else None
        logger.debug(
            "GateMiddleware: enter type=%s user=%s callback=%r text=%r",
            type(event).__name__,
            telegram_id,
            getattr(event, "data", None),
            getattr(event, "text", None),
        )
        if telegram_id is None:
            logger.debug("GateMiddleware: no telegram_id, pass through")
            return await handler(event, data)

        if is_bot_admin(telegram_id):
            logger.debug("GateMiddleware: admin bypass user=%s", telegram_id)
            return await handler(event, data)

        user = await _resolve_user(event, telegram_id)
        logger.debug(
            "GateMiddleware: loaded user=%s passed_gate=%s presentation_only=%s invite_gate=%s",
            telegram_id,
            user.passed_gate,
            settings.presentation_only,
            settings.invite_gate,
        )

        if settings.presentation_only:
            if user.passed_gate:
                logger.debug(
                    "GateMiddleware: presentation_only passed_gate bypass user=%s",
                    telegram_id,
                )
                return await handler(event, data)

            if await _is_presentation_only_allowed(event, data):
                logger.debug(
                    "GateMiddleware: presentation_only whitelist bypass user=%s",
                    telegram_id,
                )
                return await handler(event, data)

            chat_id = _resolve_chat_id(event)
            if chat_id is None:
                logger.debug(
                    "GateMiddleware: presentation_only no chat_id, pass through user=%s",
                    telegram_id,
                )
                return await handler(event, data)

            bot = data.get("bot")
            if bot is None:
                logger.debug(
                    "GateMiddleware: presentation_only no bot, pass through user=%s",
                    telegram_id,
                )
                return await handler(event, data)

            logger.debug(
                "GateMiddleware: presentation_only blocked user=%s chat_id=%s",
                telegram_id,
                chat_id,
            )
            await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
                parse_mode=None,
            )
            return None

        passed_gate = user.passed_gate or not settings.invite_gate
        if passed_gate:
            logger.debug("GateMiddleware: passed_gate bypass user=%s", telegram_id)
            return await handler(event, data)

        if await _is_regular_gate_allowed(event, data):
            logger.debug("GateMiddleware: regular gate whitelist bypass user=%s", telegram_id)
            return await handler(event, data)

        chat_id = _resolve_chat_id(event)
        if chat_id is None:
            logger.debug(
                "GateMiddleware: blocked but no chat_id, pass through user=%s",
                telegram_id,
            )
            return await handler(event, data)

        bot = data.get("bot")
        if bot is None:
            logger.debug(
                "GateMiddleware: blocked but no bot, pass through user=%s",
                telegram_id,
            )
            return await handler(event, data)

        logger.debug("GateMiddleware: blocking user=%s chat_id=%s", telegram_id, chat_id)
        await bot.send_message(
            chat_id,
            get_gate_message_text(),
            reply_markup=get_gate_keyboard(),
            parse_mode=None,
        )
        return None
