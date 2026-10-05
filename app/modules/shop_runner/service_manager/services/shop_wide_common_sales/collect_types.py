"""Типы результата сбора shop-wide common-sales за один тик."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum


class CoverageStatus(StrEnum):
    """Статус полноты покрытия текущей попытки сбора."""

    COMPLETE = "COMPLETE"
    PARTIAL_ASSORTMENT = "PARTIAL_ASSORTMENT"
    PARTIAL_API = "PARTIAL_API"
    PARTIAL_CH = "PARTIAL_CH"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class CommonSaleCollectResult:
    """Итог одного маршрута сбора (E или U) за текущую попытку."""

    updated_nmids: frozenset[int] = frozenset()
    failed_nmids: frozenset[int] = frozenset()
    returned_pairs: frozenset[tuple[int, date]] = frozenset()
    persisted_pairs: frozenset[tuple[int, date]] = frozenset()
    rejected_pair_count: int = 0
    ch_insert_failed: bool = False


@dataclass(frozen=True, slots=True)
class CollectContext:
    """Замороженный контекст валидации фактов для одного batch API."""

    attempted_nmids: frozenset[int]
    window_start: date
    window_end: date


@dataclass
class TickPartition:
    """Разбиение A/E/U на один тик."""

    assortment_nmids: frozenset[int]
    legacy_nmids: frozenset[int]
    uncovered_nmids: frozenset[int]
    assortment_pages: int = 0
    assortment_complete: bool = True
    assortment_partial_reason: str | None = None
    terminal_empty_page: bool = False


@dataclass
class TickCollectSummary:
    """Агрегированный итог координатора за тик."""

    updated_nmids: set[int] = field(default_factory=lambda: set[int]())
    failed_nmids: set[int] = field(default_factory=lambda: set[int]())
    returned_pairs: set[tuple[int, date]] = field(
        default_factory=lambda: set[tuple[int, date]]()
    )
    persisted_pairs: set[tuple[int, date]] = field(
        default_factory=lambda: set[tuple[int, date]]()
    )
    legacy_route_updated_nmids: set[int] = field(default_factory=lambda: set[int]())
    rejected_pair_count: int = 0
    coverage_status: CoverageStatus = CoverageStatus.COMPLETE
    partial_reason: str | None = None


def iter_window_dates(window_start: date, window_end: date) -> frozenset[date]:
    """Все календарные даты включительно в замороженном MSK-окне."""
    days: list[date] = []
    current = window_start
    while current <= window_end:
        days.append(current)
        current += timedelta(days=1)
    return frozenset(days)


def expected_shop_pairs(
    assortment_nmids: frozenset[int],
    window_start: date,
    window_end: date,
) -> frozenset[tuple[int, date]]:
    """Ожидаемые пары (nmid, date) для shop coverage: A × inclusive window."""
    dates = iter_window_dates(window_start, window_end)
    return frozenset((nmid, d) for nmid in assortment_nmids for d in dates)


def nmids_with_full_window(
    pairs: frozenset[tuple[int, date]] | set[tuple[int, date]],
    nmids: frozenset[int],
    window_start: date,
    window_end: date,
) -> frozenset[int]:
    """nmIDs, для которых есть все даты окна в переданном множестве пар."""
    expected_days = iter_window_dates(window_start, window_end)
    complete: set[int] = set()
    for nmid in nmids:
        if all((nmid, d) in pairs for d in expected_days):
            complete.add(nmid)
    return frozenset(complete)
