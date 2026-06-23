"""Handlers for mandatory Telegram phone collection."""

from aiogram import Bot, F, Router
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy import select

from app.client_bot.user_interface.views.phone_request import (
    get_phone_request_keyboard,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker


@router.message(F.contact)
async def save_user_phone(message: Message, bot: Bot) -> None:
    """Save the user's own Telegram contact and remove the reply keyboard."""
    if message.from_user is None or message.contact is None:
        return

    if message.contact.user_id != message.from_user.id:
        await bot.send_message(
            message.chat.id,
            "Отправьте ваш собственный номер через кнопку ниже.",
            reply_markup=get_phone_request_keyboard(),
        )
        return

    phone_number = message.contact.phone_number.strip()
    async with _sm(read_only=False) as session:
        stmt = select(User).where(User.user_telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            await bot.send_message(
                message.chat.id,
                "Пользователь не найден. Нажмите /start и повторите попытку.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        user.phone = phone_number
        await session.commit()

    await bot.send_message(
        message.chat.id,
        "Номер телефона сохранён. Теперь можно продолжить работу.",
        reply_markup=ReplyKeyboardRemove(),
    )
