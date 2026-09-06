"""Тексты и клавиатура экрана «Доступ закрыт» (гейт инвайт-системы)."""

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.const import OFFERTA_URL, SUPPORT_USER_NAME, CHAT_FOR_INVITES
from app.client_bot.user_interface.views.callbacks import Gate


def get_gate_message_text() -> str:
    """Формирует полный текст экрана гейта: заголовок, тело, подвал."""
    header = "Бесплатный бот для управления рекламой WB с возможностью полного автоуправления кампаниями"
    body = (
        "Бесплатный режим позволяет подключить токен и управлять рекламой вручную.\n"
        "Можно смотреть кампании, ставки, ключи и бюджеты, работать с Excel и ручными настройками.\n\n"
        "Платный режим подключает автоуправление, где бот сам ведёт кампании.\n\n"
        "Чтобы войти, отправьте invite code сообщением в этот чат.\n"
        "Кнопка «Ввести инвайт» не обязательна: можно просто сразу отправить код."
         f"Нет инвайта? Запросите его в чате селлеров: {CHAT_FOR_INVITES}\n"
        f"Нет инвайта? Запросите его в любом крупном чате селлеров, например, тут - {CHAT_FOR_INVITES}\n" ,
        "Напишите там:\n"
        " Нужен инвайт для МаркетОпс"
    )
    footer = (
        "Если у вас уже был доступ и его нужно восстановить, "
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
