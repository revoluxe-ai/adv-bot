"""Покрытие окна: граница пакета не доказывает полноту источника."""

from __future__ import annotations

from datetime import date


def resolve_coverage_status(
    *,
    nominal_start: date,
    nominal_end: date,
    observed_dates: set[date],
    source_complete_through: date | None,
    force_partial: bool,
) -> str:
    """``COMPLETE`` только если источник доказал каждый номинальный день.

    Совпадение ``nominal_end`` с границей пакета само по себе статус не поднимает:
    без ``source_complete_through`` полное покрытие закрыто.
    """
    if nominal_end < nominal_start:
        return "NO_DATA"
    observed = {day for day in observed_dates if nominal_start <= day <= nominal_end}
    if not observed:
        return "NO_DATA"
    requested = (nominal_end - nominal_start).days + 1
    proven = (
        source_complete_through is not None
        and nominal_end <= source_complete_through
        and len(observed) == requested
        and not force_partial
    )
    if proven:
        return "COMPLETE"
    return "PARTIAL"


def effective_range(
    *,
    nominal_start: date,
    nominal_end: date,
    observed_dates: set[date],
    source_complete_through: date | None,
) -> tuple[date | None, date | None]:
    """Пересечение номинального окна с днями, которые источник реально отдал.

    Если полнота доказана только до даты, дни после неё в эффективный диапазон
    не входят: их наличие не делает хвост окна полным.
    """
    observed = [day for day in observed_dates if nominal_start <= day <= nominal_end]
    if source_complete_through is not None:
        observed = [day for day in observed if day <= source_complete_through]
    if not observed:
        return None, None
    return min(observed), max(observed)
