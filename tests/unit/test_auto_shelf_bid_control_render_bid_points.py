"""Unit-тесты лимита и сортировки блока «Покрытые ставки» в Telegram."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    render_auto_shelf_bid_control_message,
    select_bid_points_for_telegram,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    BidPointStatsDTO,
)

pytestmark = pytest.mark.unit


def _point(
    bid_minor: int,
    *,
    impressions: int,
    is_covered: bool,
    at: datetime,
) -> BidPointStatsDTO:
    return BidPointStatsDTO(
        bid_minor=bid_minor,
        currency="RUB",
        last_interval_at=at,
        impressions=impressions,
        clicks=0,
        carts=0,
        orders=0,
        spend=1.0,
        cart_cpa=1.0,
        ctr=None,
        cart_cr=None,
        is_covered=is_covered,
        is_best=False,
        is_current_main=False,
        is_current_test=False,
    )


def test_select_bid_points_returns_five_most_recent_covered() -> None:
    base = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    points = [
        _point(10_000, impressions=600, is_covered=True, at=base),
        _point(20_000, impressions=600, is_covered=True, at=base.replace(hour=11)),
        _point(30_000, impressions=600, is_covered=True, at=base.replace(hour=12)),
        _point(40_000, impressions=600, is_covered=True, at=base.replace(hour=13)),
        _point(50_000, impressions=600, is_covered=True, at=base.replace(hour=14)),
        _point(60_000, impressions=600, is_covered=True, at=base.replace(hour=15)),
        _point(70_000, impressions=100, is_covered=False, at=base.replace(hour=16)),
    ]
    selected = select_bid_points_for_telegram(points, limit=5)
    assert [p.bid_minor for p in selected] == [
        60_000,
        50_000,
        40_000,
        30_000,
        20_000,
    ]


def test_render_shows_truncation_hint_when_more_than_five_points() -> None:
    from tests.unit.test_auto_shelf_bid_control_render_message import _view_with_bid_point

    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    points = [
        _point(
            20_000 + i * 100,
            impressions=600,
            is_covered=True,
            at=base.replace(minute=i),
        )
        for i in range(7)
    ]
    view = replace(
        _view_with_bid_point(),
        bid_points=points,
        bid_points_total=7,
        covered_points_count=7,
    )
    text = render_auto_shelf_bid_control_message(view)
    assert "Покрытые ставки (последние 5):" in text
    assert "… ещё 2 (всего 7)" in text
