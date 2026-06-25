"""Сортировка ключей V3: shop-runner (MIN_CPO) и Telegram UI (pay_for_order asc)."""

from __future__ import annotations

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

_HARD_STATUS_WHITE_LIST = 2


def pay_for_order_sort_key(kw: CalculatedKeyword) -> tuple[float, int]:
    """Ключ сортировки: дешёвые сверху; ``None`` pay_for_order — в конец."""
    pfo = kw.pay_for_order
    pay = float("inf") if pfo is None else float(pfo)
    ks_id = int(kw.keyword_setting_original_id or 0)
    return (pay, ks_id)


def sort_white_list_by_min_cpo(
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    """Белый список (``hard_status == 2``), сортировка по возрастанию ``pay_for_order``."""
    wl = [kw for kw in keywords if int(kw.hard_status) == _HARD_STATUS_WHITE_LIST]
    return sorted(wl, key=pay_for_order_sort_key)


def sort_keywords_by_pay_for_order(
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    """Список ключей UI V3: по возрастанию ``pay_for_order`` (``None`` — в конец).

    Args:
        keywords: Отображаемые ключи (уже отфильтрованы в UI).

    Returns:
        Новый отсортированный список (исходный не мутируется).
    """
    return sorted(keywords, key=pay_for_order_sort_key)
