"""UI helpers for mandatory Telegram phone collection."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_phone_request_text() -> str:
    """Return the text shown when the bot requires a user's phone number."""
    return "Для продолжения работы отправьте ваш номер телефона кнопкой ниже."


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Build a one-button reply keyboard that requests the user's contact."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Отправить номер телефона",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
