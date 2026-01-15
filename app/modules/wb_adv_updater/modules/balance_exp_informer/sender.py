from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
import logging

from app.client_bot.notification_sender import NotificationSender

logger = logging.getLogger(__name__)


async def send_chunk(
    sender: NotificationSender,
    user_telegram_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    success = await sender.send_message(
        user_telegram_id,
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    if not success:
        logger.error(
            "Notification sender failed to deliver balance reminder to user %s",
            user_telegram_id,
        )
        raise RuntimeError("Notification sender could not deliver balance reminder")
