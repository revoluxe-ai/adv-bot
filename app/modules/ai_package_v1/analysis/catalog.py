"""Каталог окон анализа: тот же календарь, что у ключевой истории.

Номинальный конец стандартного окна — UTC-дата сборки минус один день.
Это не скользящие 24 часа и не полнота источника.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.windows.engine import (
    ROLLING_WINDOWS,
    WindowSpec,
    build_window_catalog,
)

STANDARD_ROLLING_IDS: tuple[str, ...] = tuple(ROLLING_WINDOWS)


def elapsed_previous_year(end: date) -> tuple[date, date]:
    """Тот же календарный отрезок прошлого года, что и year-to-date.

    Совпадает с выравниванием ключевой истории: 29 февраля сдвигается на 28.
    """
    prev_year = end.year - 1
    prev_start = date(prev_year, 1, 1)
    try:
        comparable_end = date(prev_year, end.month, end.day)
    except ValueError:
        comparable_end = date(prev_year, end.month, 28)
    return prev_start, comparable_end


def build_analysis_windows(
    cutoff: PackageCutoff,
    *,
    campaign_first: date | None,
    campaign_last: date | None,
    requested_period: ExportPeriod | None,
) -> list[WindowSpec]:
    """Каталог витрин ноги и охвата пакета.

    Дополнительные ``calendar_year_YYYY`` живут только на этом зерне.
    Ключевая витрина их не получает.
    """
    last_closed = cutoff.last_closed_calendar_day
    bounded_last = None
    if campaign_last is not None:
        bounded_last = min(campaign_last, last_closed)
    specs = build_window_catalog(cutoff, campaign_first, bounded_last)
    ytd_end = last_closed
    prev_start, prev_end = elapsed_previous_year(ytd_end)
    specs.append(
        WindowSpec(
            "prev_year_to_date",
            prev_start,
            prev_end,
            requested_days=(prev_end - prev_start).days + 1,
        )
    )
    specs.extend(
        _older_calendar_years(
            anchor_year=cutoff.package_cutoff_date.year,
            first=campaign_first,
            last=bounded_last,
        )
    )
    if requested_period is not None:
        span = (requested_period.end - requested_period.start).days + 1
        specs.append(
            WindowSpec(
                "requested_custom",
                requested_period.start,
                requested_period.end,
                requested_days=max(span, 0),
            )
        )
    return specs


def preset_window_ids(cutoff: PackageCutoff) -> frozenset[str]:
    """Идентификаторы принятого каталога без произвольного периода."""
    specs = build_window_catalog(cutoff, None, None)
    return frozenset(spec.window_id for spec in specs)


def custom_period_includes_watermark(
    period: ExportPeriod,
    cutoff: PackageCutoff,
) -> bool:
    """Произвольный период захватывает дату сборки или день после закрытой границы."""
    watermark = cutoff.package_cutoff_date
    if period.start <= watermark <= period.end:
        return True
    return period.end > cutoff.last_closed_calendar_day


def _older_calendar_years(
    *,
    anchor_year: int,
    first: date | None,
    last: date | None,
) -> list[WindowSpec]:
    """Годы старше позапрошлого, если они пересекают доступную историю ног."""
    if first is None or last is None:
        return []
    newest = anchor_year - 3
    if newest < first.year:
        return []
    specs: list[WindowSpec] = []
    for year in range(first.year, newest + 1):
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        if end < first or start > last:
            continue
        days = 366 if calendar.isleap(year) else 365
        specs.append(WindowSpec(f"calendar_year_{year}", start, end, requested_days=days))
    return specs


def dates_in_window(start: date, end: date, observed: set[date]) -> list[date]:
    """Наблюдаемые дни внутри включительных границ, по возрастанию."""
    return sorted(day for day in observed if start <= day <= end)


def window_day_count(start: date, end: date) -> int:
    """Число номинальных календарных дней, включая оба конца."""
    if end < start:
        return 0
    return (end - start).days + 1


def shift_back(start: date, days: int) -> date:
    """Начало окна длиной ``days``, заканчивающегося накануне ``start``."""
    return start - timedelta(days=days)
