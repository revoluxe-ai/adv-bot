"""Handlers for mandatory Telegram phone collection."""

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.callback_replay import replay_serialized_callback
from app.client_bot.user_interface.views.phone_request import (
    get_phone_request_keyboard,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker
logger = logging.getLogger(__name__)


async def save_user_phone_in_session(
    session: AsyncSession, telegram_id: int, phone_number: str
) -> User | None:
    """Persist phone for an existing user (WRITE seam).

    Args:
        session: injectable async session (``sm(read_only=False)``).
        telegram_id: Telegram user id.
        phone_number: normalized phone string to store.

    Returns:
        Updated User, or None when the user row is missing.
    """
    stmt = select(User).where(User.user_telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return None
    user.phone = phone_number
    await session.commit()
    return user


@router.message(F.contact)
async def save_user_phone(
    message: Message,
    bot: Bot,
    state: FSMContext,
    dispatcher: Dispatcher,
) -> None:
    """Save the user's own Telegram contact and remove the reply keyboard."""
    if message.from_user is None or message.contact is None:
        return

    logger.debug(
        "save_user_phone: received contact user=%s contact_user=%s",
        message.from_user.id,
        message.contact.user_id,
    )

    if message.contact.user_id != message.from_user.id:
        await bot.send_message(
            message.chat.id,
            "Отправьте ваш собственный номер через кнопку ниже.",
            reply_markup=get_phone_request_keyboard(),
        )
        return

    phone_number = message.contact.phone_number.strip()
    async with _sm(read_only=False) as session:
        user = await save_user_phone_in_session(
            session, message.from_user.id, phone_number
        )
    if user is None:
        await bot.send_message(
            message.chat.id,
            "Пользователь не найден. Нажмите /start и повторите попытку.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    logger.debug("save_user_phone: phone saved user=%s", message.from_user.id)

    pending_callback = (await state.get_data()).get("pending_phone_callback")
    await state.update_data(pending_phone_callback=None)
    logger.debug(
        "save_user_phone: pending callback exists user=%s has_pending=%s",
        message.from_user.id,
        bool(pending_callback),
    )
    await bot.send_message(
        message.chat.id,
        "Номер телефона сохранён.",
        reply_markup=ReplyKeyboardRemove(),
    )
    if not pending_callback:
        return

    await asyncio.sleep(0.3)
    logger.debug(
        "save_user_phone: replay callback user=%s data=%r",
        message.from_user.id,
        pending_callback,
    )
    await replay_serialized_callback(
        bot,
        pending_callback,
        dispatcher=dispatcher,
    )
