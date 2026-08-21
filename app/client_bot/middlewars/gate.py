"""Invite-gate middleware for users without ``User.passed_gate``.

Rollout contract (``add-free-ui-bot-access-guards`` / invite-gate-deferred):

- **Prod path today:** ``settings.invite_gate`` default ``False`` → early return
  L137–139 (no-op). Channel + phone middleware — реальные entry gates.
- **Код ниже L137** (``passed_gate``, gate screen, orphan pass-through) —
  dormant legacy / ``re-enable-invite-gate`` only. Static review MUST NOT treat
  orphan ``chat_id``/``bot`` pass-through as a prod defect while invite gate is off.
- Decision: ``openspec/changes/add-free-ui-bot-access-guards/decisions/invite-gate-deferred/decision.md``
"""

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


async def _is_regular_gate_allowed(
    event: Message | CallbackQuery,
    data: dict[str, Any],
) -> bool:
    """Whitelist classic invite-gate entry points before passed_gate."""
    if isinstance(event, Message):
        if is_start_command_message(event):
            return True
        if getattr(event, "successful_payment", None) is not None:
            return True
        state_name = await _message_state_name(data)
        return bool(state_name and state_name.startswith("GateInvite:"))

    return bool(event.data and event.data.startswith("gate:"))


class GateMiddleware(BaseMiddleware):
    """Block non-whitelisted access until the user passes the invite gate.

    **Rollout (invite deferred):** ``invite_gate`` default False → L137 early
    return; this class is a no-op in prod. Blocking logic below is dormant until
    ``INVITE_GATE=true`` with owner GO.
    """

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

        # INVITE DEFERRED: prod/stage rollout — default off; см. module docstring.
        if not settings.invite_gate:
            logger.debug("GateMiddleware: invite_gate off, pass through user=%s", telegram_id)
            return await handler(event, data)

        if is_bot_admin(telegram_id):
            logger.debug("GateMiddleware: admin bypass user=%s", telegram_id)
            return await handler(event, data)

        user = await _resolve_user(event, telegram_id)
        logger.debug(
            "GateMiddleware: loaded user=%s passed_gate=%s invite_gate=%s",
            telegram_id,
            user.passed_gate,
            settings.invite_gate,
        )

        if user.passed_gate:
            logger.debug("GateMiddleware: passed_gate bypass user=%s", telegram_id)
            return await handler(event, data)

        if await _is_regular_gate_allowed(event, data):
            logger.debug("GateMiddleware: regular gate whitelist bypass user=%s", telegram_id)
            return await handler(event, data)

        # --- INVITE-GATE-ONLY (dormant while invite_gate=False; not prod path) ---
        # The two pass-through branches below are a legacy escape hatch for
        # re-enable-invite-gate: an event that cannot receive the gate screen
        # must not trigger a broken send attempt. They are intentionally left
        # unchanged while INVITE_GATE is deferred/off by default. Do not report
        # them as a current access-control bypass: this block is unreachable on
        # the active rollout path. Before explicitly re-enabling invite_gate,
        # replace both branches with a fail-closed response in a separate
        # owner-approved change (TODO(re-enable-invite-gate)).
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
