"""Единая проверка Telegram-команды /start и /start@<bot_username>."""

from aiogram.types import Message


def is_start_command_text(text: str | None) -> bool:
    """True, если строка (целиком или первый токен) — команда /start.

    Регистр первого токена не учитывается (/Start и /start эквивалентны).
    Пустая и пробельная строка дают False.
    """
    if text is None:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    first_token = stripped.split(maxsplit=1)[0].lower()
    return first_token == "/start" or first_token.startswith("/start@")


def is_start_command_message(message: Message) -> bool:
    """True, если /start в text или caption сообщения."""
    raw = message.text if message.text is not None else message.caption
    if not isinstance(raw, str):
        return False
    return is_start_command_text(raw)
