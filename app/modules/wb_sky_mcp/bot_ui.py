"""Тексты и клавиатуры согласия ChatGPT. Секреты в текст не попадают.

Лимиты Telegram: текст 4096, callback_data 64 байта UTF-8.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.wb_sky_mcp.connection_logic import McpConnectionState

CONFIRM_PREFIX = "mcpok:"
CANCEL_PREFIX = "mcpno:"
DISCONNECT_PREFIX = "mcpdc:"
_MAX_CONNECTIONS_SHOWN = 8
_TEXT_LIMIT = 4096
_CALLBACK_LIMIT = 64


def callback_confirm(txn_id: str) -> str:
    """callback_data подтверждения. Длина проверяется отдельно."""
    return f"{CONFIRM_PREFIX}{txn_id}"


def callback_cancel(txn_id: str) -> str:
    """callback_data отмены."""
    return f"{CANCEL_PREFIX}{txn_id}"


def callback_disconnect(connection_id: str) -> str:
    """callback_data отключения одного подключения."""
    return f"{DISCONNECT_PREFIX}{connection_id}"


def assert_callback_fits(data: str) -> None:
    """Убедиться, что callback умещается в лимит Telegram."""
    size = len(data.encode("utf-8"))
    if size < 1 or size > _CALLBACK_LIMIT:
        raise ValueError("callback_data exceeds Telegram limit")


def consent_text() -> str:
    """Экран согласия. Не содержит билет, код и токен."""
    text = (
        "ChatGPT запрашивает доступ только на чтение WB Sky.\n"
        "Подтверждение свяжет этот чат с вашей учётной записью.\n"
        "Запись рекламы и изменение кампаний через ChatGPT недоступны.\n"
        "Открытие этой ссылки само по себе доступ не выдаёт.\n"
        "Нажмите «Подтвердить» или «Отмена»."
    )
    if len(text) > _TEXT_LIMIT:
        raise ValueError("consent text exceeds Telegram limit")
    return text


def consent_keyboard(txn_id: str) -> InlineKeyboardMarkup:
    """Кнопки подтверждения и отмены."""
    confirm = callback_confirm(txn_id)
    cancel = callback_cancel(txn_id)
    assert_callback_fits(confirm)
    assert_callback_fits(cancel)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data=confirm),
                InlineKeyboardButton(text="Отмена", callback_data=cancel),
            ]
        ]
    )


def return_text() -> str:
    """Текст после подтверждения. Билет живёт только в URL кнопки."""
    text = (
        "Подключение подтверждено.\n"
        "Вернитесь в ChatGPT по кнопке ниже. "
        "Ссылка одноразовая и скоро истечёт."
    )
    if len(text) > _TEXT_LIMIT:
        raise ValueError("return text exceeds Telegram limit")
    return text


def return_keyboard(complete_url: str) -> InlineKeyboardMarkup:
    """Кнопка-ссылка возврата. URL не дублируется в тексте сообщения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Вернуться в ChatGPT", url=complete_url)]
        ]
    )


def cancel_text() -> str:
    """Текст отмены без сырого идентификатора транзакции."""
    text = "Подключение ChatGPT отменено. Доступ не выдан."
    if len(text) > _TEXT_LIMIT:
        raise ValueError("cancel text exceeds Telegram limit")
    return text


def expired_text() -> str:
    """Ошибка протухшей ссылки. Идентификатор транзакции не цитируется."""
    text = (
        "Ссылка подключения устарела или уже использована. "
        "Начните подключение заново из ChatGPT."
    )
    if len(text) > _TEXT_LIMIT:
        raise ValueError("expired text exceeds Telegram limit")
    return text


def explain_text() -> str:
    """Подсказка, что учётные данные выпускает только поток из ChatGPT."""
    text = (
        "Подключение ChatGPT начинается в ChatGPT, не в этом меню.\n"
        "Здесь можно посмотреть уже выданные подключения и отключить их.\n"
        "Эта команда не создаёт токен доступа."
    )
    if len(text) > _TEXT_LIMIT:
        raise ValueError("explain text exceeds Telegram limit")
    return text


def connections_text(rows: list[McpConnectionState]) -> str:
    """Список подключений. Длинный список обрезается явно, без сырого refresh."""
    active = [row for row in rows if row.revoked_at is None]
    if not active:
        body = "Активных подключений ChatGPT нет."
    else:
        shown = active[:_MAX_CONNECTIONS_SHOWN]
        lines = ["Активные подключения ChatGPT:"]
        for row in shown:
            short = row.public_id[:8]
            created = row.created_at.strftime("%Y-%m-%d")
            lines.append(f"• {short}… с {created}")
        hidden = len(active) - len(shown)
        if hidden > 0:
            lines.append(f"Ещё подключений скрыто: {hidden}.")
        body = "\n".join(lines)
    if len(body) > _TEXT_LIMIT:
        raise ValueError("connections text exceeds Telegram limit")
    return body


def connections_keyboard(rows: list[McpConnectionState]) -> InlineKeyboardMarkup | None:
    """Кнопки отключения для показанных активных подключений."""
    active = [row for row in rows if row.revoked_at is None][:_MAX_CONNECTIONS_SHOWN]
    if not active:
        return None
    buttons: list[list[InlineKeyboardButton]] = []
    for row in active:
        data = callback_disconnect(row.public_id)
        assert_callback_fits(data)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"Отключить {row.public_id[:8]}",
                    callback_data=data,
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def disconnected_text() -> str:
    """Короткое подтверждение отключения без токена."""
    text = "Подключение ChatGPT отключено. Старый доступ больше не действует."
    if len(text) > _TEXT_LIMIT:
        raise ValueError("disconnect text exceeds Telegram limit")
    return text


def disabled_text() -> str:
    """Канал выключен флагом. Учётные данные не выпускаются."""
    text = "Подключение ChatGPT сейчас выключено."
    if len(text) > _TEXT_LIMIT:
        raise ValueError("disabled text exceeds Telegram limit")
    return text
