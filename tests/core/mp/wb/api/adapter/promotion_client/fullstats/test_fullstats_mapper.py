"""Unit tests for fullstats v3 mapper (FullStatsItem -> FullAdvStat)."""

from datetime import date

import pytest

from app.core.mp.wb.api.adapter.promotion_client.fullstats.mapper import (
    full_stats_item_to_full_adv_stat,
    _parse_date,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    FullStatsItem,
)


def test_full_stats_item_to_full_adv_stat_basic() -> None:
    """Map minimal FullStatsItem to FullAdvStat."""
    item = FullStatsItem(
        advert_id=10524818,
        views=100,
        clicks=2,
        ctr=2.0,
        cpc=50.0,
        sum_=100.0,
        atbs=1,
        orders=0,
        cr=0.0,
        shks=0,
        sum_price=0.0,
        canceled=0,
        days=[],
    )
    begin = date(2025, 3, 1)
    end = date(2025, 3, 2)
    result = full_stats_item_to_full_adv_stat(item, begin, end)
    assert result.advertId == 10524818
    assert result.views == 100
    assert result.clicks == 2
    assert result.sum == 100.0
    assert result.dates == ["2025-03-01", "2025-03-02"]
    assert result.days == []


def test_full_stats_item_to_full_adv_stat_with_days() -> None:
    """Map FullStatsItem with days array to FullAdvStat."""
    item = FullStatsItem(
        advert_id=1,
        views=50,
        clicks=1,
        ctr=2.0,
        cpc=10.0,
        sum_=10.0,
        atbs=0,
        orders=0,
        cr=0.0,
        shks=0,
        sum_price=0.0,
        canceled=0,
        days=[
            {
                "date": "2025-03-01",
                "views": 25,
                "clicks": 0,
                "ctr": 0,
                "cpc": 0,
                "sum": 5.0,
                "atbs": 0,
                "orders": 0,
                "cr": 0,
                "shks": 0,
                "sum_price": 0,
            },
            {
                "date": "2025-03-02T12:00:00",
                "views": 25,
                "clicks": 1,
                "ctr": 4.0,
                "cpc": 10.0,
                "sum": 5.0,
                "atbs": 0,
                "orders": 0,
                "cr": 0,
                "shks": 0,
                "sum_price": 0,
            },
        ],
    )
    begin = date(2025, 3, 1)
    end = date(2025, 3, 2)
    result = full_stats_item_to_full_adv_stat(item, begin, end)
    assert len(result.days) == 2
    assert result.days[0].views == 25 and result.days[0].sum == 5.0
    assert result.days[1].clicks == 1 and result.days[1].cpc == 10.0


def test_parse_date_negative_offset() -> None:
    """Negative UTC offset (e.g. -05:00) must be parsed; previously caused ValueError and dropped days."""
    from datetime import datetime

    parsed = _parse_date("2023-10-06T03:00:00-05:00")
    assert parsed == datetime(2023, 10, 6, 3, 0, 0)
    assert parsed.tzinfo is None


def test_days_with_negative_offset_included() -> None:
    """Day with date string using negative offset must be included in result (not silently dropped)."""
    item = FullStatsItem(
        advert_id=1,
        views=10,
        clicks=0,
        ctr=0,
        cpc=0,
        sum_=0,
        atbs=0,
        orders=0,
        cr=0,
        shks=0,
        sum_price=0,
        canceled=0,
        days=[
            {"date": "2025-03-01T00:00:00-05:00", "views": 10, "clicks": 0, "ctr": 0, "cpc": 0, "sum": 0, "atbs": 0, "orders": 0, "cr": 0, "shks": 0, "sum_price": 0},
        ],
    )
    begin = date(2025, 3, 1)
    end = date(2025, 3, 1)
    result = full_stats_item_to_full_adv_stat(item, begin, end)
    assert len(result.days) == 1
    assert result.days[0].views == 10
