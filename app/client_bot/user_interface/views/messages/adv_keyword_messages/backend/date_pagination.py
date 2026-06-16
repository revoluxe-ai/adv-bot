"""Утилиты пагинации дневной статистики по датам.

Модуль выносит общий расчёт количества страниц и диапазона дат, чтобы экраны
дневной статистики в клиентском боте использовали одинаковую логику.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def get_total_pages(
    earliest_date: date | None,
    page_size: int = 14,
    today: date | None = None,
) -> int:
    """Возвращает количество страниц для диапазона от `earliest_date` до сегодня."""
    if earliest_date is None:
        return 1
    today = today or datetime.now().date()
    delta_days = (today - earliest_date).days + 1
    return max(1, (delta_days + page_size - 1) // page_size)


def page_to_date_range(
    page: int,
    page_size: int = 14,
    earliest_date: date | None = None,
    today: date | None = None,
) -> tuple[date, date] | None:
    """Возвращает границы дат для страницы статистики.

    Page 1 соответствует последним `page_size` дням, page 2 — предыдущим
    `page_size` дням и так далее.
    """
    today = today or datetime.now().date()
    shift_days = (max(page, 1) - 1) * page_size
    end_date = today - timedelta(days=shift_days)
    if earliest_date is not None and end_date < earliest_date:
        return None

    start_date = end_date - timedelta(days=page_size - 1)
    if earliest_date is not None and start_date < earliest_date:
        start_date = earliest_date
    if start_date > end_date:
        return None
    return start_date, end_date
