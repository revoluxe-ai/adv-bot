from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
import logging


logger = logging.getLogger(__name__)

async def send_chunk(
    bot: Bot,
    user_telegram_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    try:
        _ = await bot.send_message(
            chat_id=user_telegram_id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
    except Exception:
        logger.exception("Ошибка при отправке сообщения об истекающем балансе")
        raise
    return None
