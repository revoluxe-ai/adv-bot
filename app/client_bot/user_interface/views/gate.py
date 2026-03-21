"""Тексты и клавиатура экрана «Доступ закрыт» (гейт инвайт-системы)."""

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.const import OFFERTA_URL, SUPPORT_USER_NAME
from app.client_bot.user_interface.views.callbacks import Gate


def get_gate_message_text() -> str:
    """Формирует полный текст экрана гейта: заголовок, тело, подвал."""
    header = "🔒 Доступ закрыт"
    body = (
        "Чтобы пользоваться сервисом, нужен инвайт-код.\n\n"
        "Нажмите «Ввести инвайт» и отправьте код одним сообщением."
    )
    footer = (
        "Если вы уже работали с сервисом и считаете, что доступ должен быть — "
        'нажмите «Восстановить доступ».'
    )
    return f"{header}\n\n{body}\n\n{footer}"


def get_gate_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура экрана гейта: по одной кнопке на строке."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Ввести инвайт",
                    callback_data=Gate(action="invite_enter").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Оферта",
                    url=OFFERTA_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Восстановить доступ",
                    url=f"""https://t.me/{SUPPORT_USER_NAME}?text={quote("Восстановление доступа "
                                                                         "в сервис, ситуация такая: ")}""",
                )
            ],
        ]
    )
