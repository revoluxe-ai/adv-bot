"""Unit tests for full_adv_stat_utils (contiguity check and filter to dates)."""

from datetime import date, datetime

import pytest

from app.modules.full_stat_adv_updater.full_adv_stat_utils import (
    filter_full_adv_stat_to_dates,
    requested_dates_are_contiguous,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import (
    DayStats,
    FullAdvStat,
)


def test_requested_dates_are_contiguous_empty_or_single() -> None:
    assert requested_dates_are_contiguous([]) is True
    assert requested_dates_are_contiguous([date(2025, 3, 1)]) is True


def test_requested_dates_are_contiguous_full_range() -> None:
    dates = [date(2025, 3, 1), date(2025, 3, 2), date(2025, 3, 3)]
    assert requested_dates_are_contiguous(dates) is True


def test_requested_dates_are_contiguous_non_contiguous() -> None:
    # Only day 1 and day 31, missing days 2–30
    dates = [date(2025, 3, 1), date(2025, 3, 31)]
    assert requested_dates_are_contiguous(dates) is False

    dates = [date(2025, 3, 1), date(2025, 3, 3)]  # missing day 2
    assert requested_dates_are_contiguous(dates) is False


def test_filter_full_adv_stat_to_dates_non_contiguous() -> None:
    """Filter re-aggregates to only requested dates (day 1 and day 31)."""
    day1 = DayStats(
        date=datetime(2025, 3, 1),
        views=10,
        clicks=1,
        ctr=10.0,
        cpc=5.0,
        sum=5.0,
        atbs=0,
        orders=0,
        cr=0.0,
        shks=0,
        sum_price=0.0,
    )
    day2 = DayStats(
        date=datetime(2025, 3, 2),
        views=100,
        clicks=10,
        ctr=10.0,
        cpc=5.0,
        sum=50.0,
        atbs=1,
        orders=1,
        cr=10.0,
        shks=1,
        sum_price=100.0,
    )
    day31 = DayStats(
        date=datetime(2025, 3, 31),
        views=20,
        clicks=2,
        ctr=10.0,
        cpc=5.0,
        sum=10.0,
        atbs=0,
        orders=0,
        cr=0.0,
        shks=0,
        sum_price=0.0,
    )
    stat = FullAdvStat(
        dates=["2025-03-01", "2025-03-02", "2025-03-31"],
        views=130,
        clicks=13,
        ctr=10.0,
        cpc=5.0,
        sum=65.0,
        atbs=1,
        orders=1,
        cr=10.0,
        shks=1,
        sum_price=100.0,
        days=[day1, day2, day31],
        boosterStats=None,
        advertId=42,
    )
    requested = [date(2025, 3, 1), date(2025, 3, 31)]
    filtered = filter_full_adv_stat_to_dates([stat], requested)
    assert len(filtered) == 1
    out = filtered[0]
    assert out.advertId == 42
    assert out.views == 30  # 10 + 20 (day1 + day31 only)
    assert out.clicks == 3
    assert out.sum == 15.0
    assert out.dates == ["2025-03-01", "2025-03-31"]
    assert len(out.days) == 2
    assert _day_date(out.days[0]) == date(2025, 3, 1)
    assert _day_date(out.days[1]) == date(2025, 3, 31)


def _day_date(d: DayStats) -> date:
    val = d.date
    return val.date() if isinstance(val, datetime) else val
