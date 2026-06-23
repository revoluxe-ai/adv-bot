"""Middleware that blocks bot usage until the Telegram phone is stored."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.client_bot.user_interface.views.phone_request import (
    get_phone_request_keyboard,
    get_phone_request_text,
)
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker


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
        if telegram_id is None:
            return await handler(event, data)

        async with _sm(read_only=True) as session:
            stmt = select(User).options(load_only(User.passed_gate, User.phone)).where(
                User.user_telegram_id == telegram_id
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

        if user is None:
            return await handler(event, data)

        access_granted = user.passed_gate or not settings.invite_gate
        if access_granted is False or user.phone:
            return await handler(event, data)

        if isinstance(event, Message) and getattr(event, "contact", None) is not None:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            state = data.get("state")
            if isinstance(state, FSMContext):
                await state.update_data(
                    pending_phone_callback=json.dumps(
                        event.model_dump(mode="json", exclude_none=True)
                    )
                )

        bot = data.get("bot")
        if bot is None:
            return await handler(event, data)

        if isinstance(event, Message):
            chat_id = event.chat.id
        else:
            chat_id = (
                event.message.chat.id
                if event.message and event.message.chat
                else telegram_id
            )

        await bot.send_message(
            chat_id,
            get_phone_request_text(),
            reply_markup=get_phone_request_keyboard(),
        )
        return None
