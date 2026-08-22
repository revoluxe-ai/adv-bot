"""Telegram payloads для shelf-exhausted pause / «Сбросить паузу».

Spec: ``auto-shelf-exhausted-pause`` (notify + кнопка).
Limits: ``openspec/policies/telegram_bot_api_limits.md``.
"""

from __future__ import annotations

import html
from datetime import datetime

from .decision import ResolveCpoKind

RESET_PAUSE_BUTTON_TEXT = "Сбросить паузу"

# callback_data prefix; полный payload собирается с adv_setting id.
_RESET_CALLBACK_PREFIX = "asb_exh_reset"


def build_shelf_exhausted_reset_callback_data(adv_setting_original_id: int) -> str:
    """Inline callback_data для кнопки «Сбросить паузу» (≤64 UTF-8 bytes)."""
    return f"{_RESET_CALLBACK_PREFIX}:{int(adv_setting_original_id)}"


def _kind_ru(kind: ResolveCpoKind | str) -> str:
    if kind == "target":
        return "целевой"
    if kind == "max":
        return "максимальный"
    return str(kind)


def build_shelf_exhausted_pause_message(
    *,
    shop_name: str,
    campaign_name: str,
    resolve_cpo_kind: ResolveCpoKind | str,
    resolve_cpo_value: float,
    due_at: datetime | None,
    parse_mode: str = "HTML",
) -> str:
    """Текст notify при входе в shelf-exhausted pause (HTML-escaped).

    Args:
        shop_name: имя магазина (worst-case длинное).
        campaign_name: имя/метка кампании.
        resolve_cpo_kind: target|max — какой порог зафиксировали.
        resolve_cpo_value: значение resolve CPO в рублях.
        due_at: календарный перетест (UTC/aware); None → «по настройке».
        parse_mode: ожидаемый режим (HTML по умолчанию).

    Returns:
        Готовый текст без сырых технических имён adapters/enums.
    """
    _ = parse_mode
    shop = html.escape(shop_name or "магазин")
    camp = html.escape(campaign_name or "кампания")
    kind = _kind_ru(resolve_cpo_kind)
    cpo = f"{float(resolve_cpo_value):.2f}"
    if due_at is not None:
        due_txt = html.escape(due_at.strftime("%d.%m.%Y %H:%M UTC"))
    else:
        due_txt = "по календарю из настроек полок"
    return (
        f"⏸ Авто на паузе: тест полок исчерпан, нет ставки под план.\n"
        f"Магазин: <b>{shop}</b>\n"
        f"Кампания: <b>{camp}</b>\n"
        f"Допустимый CPO ({kind}): <b>{cpo}</b> ₽\n"
        f"Следующий перетест: <b>{due_txt}</b>\n"
        f"Модуль «Управление ставкой в полках» остаётся включённым.\n"
        f"Кнопка «{RESET_PAUSE_BUTTON_TEXT}» снимет только этот блок паузы."
    )
