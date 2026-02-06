"""Тексты и клавиатура экрана «Доступ закрыт» (гейт инвайт-системы)."""

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.const import GATE_ENTRY_AMOUNT, OFFERTA_URL, SUPPORT_USER_NAME
from app.client_bot.user_interface.views.callbacks import Gate


def get_gate_message_text(entry_amount: int = GATE_ENTRY_AMOUNT) -> str:
    """Формирует полный текст экрана гейта: заголовок, тело, подвал."""
    header = "🔒 Доступ закрыт"
    body = (
        f"Чтобы пользоваться сервисом, нужен инвайт или входной платёж {entry_amount} ₽.\n\n"
        f"{entry_amount} ₽ зачисляются на ваш баланс пользователя. "
        "Далее вы можете использовать эти средства для пополнения подключенных кабинетов в сервисе.\n\n"
        "Возврат входного платежа не предусмотрен (см. оферту)."
    )
    footer = (
        "Если вы уже работали с сервисом и считаете, что доступ должен быть — "
        'нажмите «Восстановить доступ».'
    )
    return f"{header}\n\n{body}\n\n{footer}"


def get_gate_keyboard(entry_amount: int = GATE_ENTRY_AMOUNT) -> InlineKeyboardMarkup:
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
                    text=f"Входной платёж {entry_amount} ₽",
                    callback_data=Gate(action="pay_entry_amount").pack(),
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
