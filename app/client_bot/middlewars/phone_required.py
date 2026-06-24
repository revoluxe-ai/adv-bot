"""Middleware that blocks bot usage until the Telegram phone is stored."""

from collections.abc import Awaitable, Callable
import logging
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.client_bot.callback_replay import serialize_callback_query
from app.client_bot.user_interface.views.phone_request import (
    get_phone_request_keyboard,
    get_phone_request_text,
)
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker
logger = logging.getLogger(__name__)


class PhoneRequiredMiddleware(BaseMiddleware):
    """Require a saved phone for users who already have effective bot access."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event = cast(Message | CallbackQuery, event)
        telegram_id = event.from_user.id if event.from_user else None
        logger.debug(
            "PhoneRequiredMiddleware: enter type=%s user=%s callback=%r text=%r",
            type(event).__name__,
            telegram_id,
            getattr(event, "data", None),
            getattr(event, "text", None),
        )
        if telegram_id is None:
            logger.debug("PhoneRequiredMiddleware: no telegram_id, pass through")
            return await handler(event, data)

        async with _sm(read_only=True) as session:
            stmt = select(User).options(load_only(User.passed_gate, User.phone)).where(
                User.user_telegram_id == telegram_id
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

        if user is None:
            logger.debug("PhoneRequiredMiddleware: user not found, pass through user=%s", telegram_id)
            return await handler(event, data)

        access_granted = user.passed_gate or not settings.invite_gate
        logger.debug(
            "PhoneRequiredMiddleware: user=%s passed_gate=%s has_phone=%s access_granted=%s",
            telegram_id,
            user.passed_gate,
            bool(user.phone),
            access_granted,
        )
        if access_granted is False or user.phone:
            logger.debug("PhoneRequiredMiddleware: pass through user=%s", telegram_id)
            return await handler(event, data)

        if isinstance(event, Message) and getattr(event, "contact", None) is not None:
            logger.debug("PhoneRequiredMiddleware: contact message bypass user=%s", telegram_id)
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            state = data.get("state")
            if isinstance(state, FSMContext):
                await state.update_data(
                    pending_phone_callback=serialize_callback_query(event)
                )
                logger.debug(
                    "PhoneRequiredMiddleware: saved pending callback user=%s data=%r",
                    telegram_id,
                    getattr(event, "data", None),
                )

        bot = data.get("bot")
        if bot is None:
            logger.debug("PhoneRequiredMiddleware: no bot, pass through user=%s", telegram_id)
            return await handler(event, data)

        if isinstance(event, Message):
            chat_id = event.chat.id
        else:
            chat_id = (
                event.message.chat.id
                if event.message and event.message.chat
                else telegram_id
            )

        logger.debug("PhoneRequiredMiddleware: requesting phone user=%s chat_id=%s", telegram_id, chat_id)
        await bot.send_message(
            chat_id,
            get_phone_request_text(),
            reply_markup=get_phone_request_keyboard(),
        )
        return None
