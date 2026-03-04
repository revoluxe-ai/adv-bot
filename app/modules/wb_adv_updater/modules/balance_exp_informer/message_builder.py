from __future__ import annotations

from typing import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views.callbacks import AddBalance

from .dto import ReminderItem
from .levels import BalanceLevel


CHUNK_SIZE = 12


def _level_priority(item: ReminderItem) -> tuple[int, float, str]:
    level_priority = item.level
    if level_priority == BalanceLevel.EXPIRED:
        # sort more urgent (larger negative) first -> smaller days_left
        return (0, item.days_left, item.shop_name)
    if level_priority == BalanceLevel.D1:
        return (1, item.days_left, item.shop_name)
    return (2, item.days_left, item.shop_name)


def sort_items(items: Iterable[ReminderItem]) -> list[ReminderItem]:
    return sorted(items, key=_level_priority)


def chunk(items: list[ReminderItem], size: int = CHUNK_SIZE) -> list[list[ReminderItem]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _build_title(items_chunk: list[ReminderItem]) -> str:
    # Заголовок по правилу приоритетов:
    # есть хотя бы один EXPIRED → 🔴
    # иначе есть D1 → 🟡
    # иначе (только D3) → 🟢
    if any(it.level == BalanceLevel.EXPIRED for it in items_chunk):
        return "🔴 Деньги закончились"

    if any(it.level == BalanceLevel.D1 for it in items_chunk):
        return "🟡 Деньги заканчиваются"

    return "🟢 Деньги заканчиваются"


def _format_shop_line(item: ReminderItem) -> str:
    shop = item.shop_name

    if item.level == BalanceLevel.EXPIRED:
        return f"❌ {shop}: деньги закончились — реклама без контроля"

    if item.level == BalanceLevel.D1:
        return f"⚠️ {shop}: осталось меньше суток"

    # BalanceLevel.D3
    return f"⏳ {shop}: осталось меньше 3 дней"


def build_message(items_chunk: list[ReminderItem]) -> tuple[str, InlineKeyboardMarkup]:
    lines: list[str] = []
    buttons = InlineKeyboardBuilder()

    lines.append(_build_title(items_chunk))

    # короткое пояснение без противоречий
    if any(it.level == BalanceLevel.EXPIRED for it in items_chunk):
        lines.append(
            "Без пополнения бот не сможет управлять рекламой — возможен рост расходов и просадка продаж."
        )
    else:
        lines.append(
            "Пополните баланс заранее, чтобы бот не остановил управление рекламой."
        )

    lines.append("")

    for reminder in items_chunk:
        lines.append(_format_shop_line(reminder))

        button = InlineKeyboardButton(
            text=f"Пополнить • {reminder.shop_name}",
            callback_data=AddBalance(
                wb_cabinet_original_id=reminder.wb_cabinet_id
            ).pack(),
        )
        buttons.row(button)

    lines.append("")
    lines.append("Нажмите «Пополнить» напротив нужного магазина.")

    return "\n".join(lines), buttons.as_markup()


def build_negative_balance_reminder_message(
    items: list[tuple[str, int, int]],
) -> tuple[str, InlineKeyboardMarkup]:
    """items: (shop_name, wb_cabinet_id, days_left) per shop."""
    lines: list[str] = [
        "🔴 Баланс в минусе",
        "",
        "Пополните баланс или деактивируйте кампании в настройках магазина.",
        "",
    ]
    buttons = InlineKeyboardBuilder()
    for shop_name, wb_cabinet_id, days_left in items:
        lines.append(f"• {shop_name}: осталось {days_left} дн.")
        buttons.row(
            InlineKeyboardButton(
                text=f"Пополнить • {shop_name}",
                callback_data=AddBalance(wb_cabinet_original_id=wb_cabinet_id).pack(),
            )
        )
    lines.append("")
    lines.append("Нажмите «Пополнить» или отключите кампании в настройках магазина.")
    return "\n".join(lines), buttons.as_markup()
