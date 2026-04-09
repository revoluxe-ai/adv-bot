"""Уведомления саппорта/админов в Telegram."""

import logging
from datetime import UTC, datetime

from aiogram import Bot

from app.client_bot.const import MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID
from app.settings import settings

logger = logging.getLogger(__name__)


async def notify_presentation_request(
    bot: Bot,
    *,
    telegram_id: int,
    username: str | None,
) -> None:
    """Отправляет главному менеджеру заявку на презентацию (см. MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID / env)."""
    uname = f"@{username}" if username else "(без username)"
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        "Запрос презентации\n\n"
        f"Telegram ID: {telegram_id}\n"
        f"Username: {uname}\n"
        f"Время: {now}"
    )
    recipient_id = (
        settings.presentation_notify_telegram_id or MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID
    )
    try:
        await bot.send_message(recipient_id, text)
    except Exception:
        logger.exception(
            "Не удалось отправить уведомление о презентации получателю %s",
            recipient_id,
        )


async def notify_presentation_booking(
    bot: Bot,
    *,
    telegram_id: int,
    username: str | None,
    slot_text: str,
) -> None:
    """Уведомление менеджеру о брони презентации по слоту."""
    uname = f"@{username}" if username else "(без username)"
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        "Новая запись на презентацию\n\n"
        f"Telegram ID: {telegram_id}\n"
        f"Username: {uname}\n"
        f"Слот: {slot_text}\n"
        f"Время записи: {now}"
    )
    recipient_id = (
        settings.presentation_notify_telegram_id or MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID
    )
    try:
        await bot.send_message(recipient_id, text)
    except Exception:
        logger.exception(
            "Не удалось отправить уведомление о брони получателю %s",
            recipient_id,
        )
