"""Middleware гейта: блокирует доступ пользователям с User.passed_gate=False."""

from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.user_interface.views.gate import get_gate_keyboard, get_gate_message_text
from app.client_bot.utils import create_user
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker

PRESENTATION_ONLY_BLOCKED_TEXT = (
    "Доступ к функциям бота закрыт. Откройте меню через /start — запись на презентацию."
)


def _is_start_command(message: Message) -> bool:
    raw = getattr(message, "text", None)
    if not isinstance(raw, str):
        return False
    stripped = raw.strip()
    if not stripped:
        return False
    first = stripped.split(maxsplit=1)[0]
    return first == "/start" or first.startswith("/start@")


# Use centralized safe_callback_answer from callback_helpers for answering callbacks.


class GateMiddleware(BaseMiddleware):
    """В режиме presentation_only: админы и passed_gate — полный доступ; иначе whitelist заявки.

    Иначе — passed_gate и whitelist gate:* / оплата / GateInvite (классический гейт).
    """

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

        admin_ok = is_bot_admin(telegram_id)
        if admin_ok:
            return await handler(event, data)

        async with _sm(read_only=False) as session:
            stmt = select(User).options(load_only(User.passed_gate)).where(
                User.user_telegram_id == telegram_id
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                chat_id: int | None = None
                if isinstance(event, Message):
                    chat_id = event.chat.id
                elif event.message and event.message.chat:
                    chat_id = event.message.chat.id
                user = await create_user(
                    session,
                    telegram_id,
                    username=event.from_user.username if event.from_user else None,
                    adv_updater_user_chat_id=chat_id,
                )

        if settings.presentation_only:
            passed_gate_effective = user.passed_gate
            if passed_gate_effective:
                return await handler(event, data)

            if isinstance(event, Message):
                if _is_start_command(event):
                    return await handler(event, data)
                state = data.get("state")
                if state is not None:
                    current = await state.get_state()
                    if current is not None and str(current).startswith(
                        "PresentationRequest:"
                    ):
                        return await handler(event, data)
            if (
                isinstance(event, CallbackQuery)
                and event.data
                and event.data.startswith("presentation:")
            ):
                return await handler(event, data)

            if isinstance(event, Message):
                chat_id = event.chat.id
            else:
                chat_id = (
                    event.message.chat.id
                    if event.message and event.message.chat
                    else None
                )
            if chat_id is None:
                return await handler(event, data)
            bot = data.get("bot")
            if bot is None:
                return await handler(event, data)
            await bot.send_message(chat_id, PRESENTATION_ONLY_BLOCKED_TEXT)
            return None

        passed_gate = user.passed_gate
        if not settings.invite_gate:
            passed_gate = True
        if passed_gate:
            return await handler(event, data)

        # Whitelist для пользователя без passed_gate (все остальное → экран гейта):
        # 1) CallbackQuery с data "gate:*"
        # 2) Message с successful_payment
        # 3) Message в FSM GateInvite:* — ввод инвайт-кода
        if isinstance(event, CallbackQuery):
            if event.data and event.data.startswith("gate:"):
                return await handler(event, data)
        if isinstance(event, Message):
            if getattr(event, "successful_payment", None) is not None:
                return await handler(event, data)
            state = data.get("state")
            if state is not None:
                current = await state.get_state()
                if current is not None and current.startswith("GateInvite:"):
                    return await handler(event, data)

        # Блокируем: показываем экран гейта
        if isinstance(event, Message):
            chat_id = event.chat.id
        else:
            chat_id = (
                event.message.chat.id
                if event.message and event.message.chat
                else None
            )
        if chat_id is None:
            return await handler(event, data)

        bot = data.get("bot")
        if bot is None:
            return await handler(event, data)

        text = get_gate_message_text()
        keyboard = get_gate_keyboard()
        await bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard,
            parse_mode=None,
        )
        return None
