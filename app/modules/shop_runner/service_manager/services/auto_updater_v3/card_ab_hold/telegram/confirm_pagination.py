"""Пагинация confirm-экранов A/B Hold (ux contract §9, page size = 10).

Spec requirement: «Confirmation screens paginate keyword lists at a fixed page size».
Чистые функции — unit-testable без Telegram/FSM.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

PAGE_SIZE = 10

T = TypeVar("T")


def paginate(
    items: Sequence[T],
    page: int,
    *,
    page_size: int = PAGE_SIZE,
) -> tuple[list[T], int, int]:
    """Разбить ``items`` на страницы фиксированного размера.

    Args:
        items: полный список элементов (ключи, строки TP и т.д.).
        page: запрошенный номер страницы (0-based); отрицательные → 0;
            за пределами → последняя страница.
        page_size: размер страницы (по контракту 10).

    Returns:
        Кортеж ``(slice_items, normalized_page, total_pages)``.
        ``total_pages`` минимум 1 даже для пустого списка.
    """
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    normalized_page = max(0, min(int(page), total_pages - 1))
    start = normalized_page * page_size
    end = start + page_size
    return list(items[start:end]), normalized_page, total_pages
