"""Unit-тесты просмотрщика покрытых ставок цикла в Telegram."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.client_bot.user_interface.views.callbacks import AutoShelfBidControlBidPoints
from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    bid_point_viewer_page_count,
    build_bid_point_viewer_keyboard,
    clamp_bid_point_page,
    render_auto_shelf_bid_control_message,
    render_bid_point_viewer_message,
    select_covered_bid_points_for_cycle_viewer,
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


def test_main_screen_has_no_covered_bid_points_block() -> None:
    from tests.unit.test_auto_shelf_bid_control_render_message import _view_with_bid_point

    text = render_auto_shelf_bid_control_message(_view_with_bid_point())
    assert "Покрытые ставки:" not in text
    assert "… ещё" not in text


def test_select_covered_bid_points_for_cycle_viewer_only_covered_sorted() -> None:
    base = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    points = [
        _point(10_000, impressions=600, is_covered=True, at=base),
        _point(20_000, impressions=100, is_covered=False, at=base.replace(hour=16)),
        _point(30_000, impressions=600, is_covered=True, at=base.replace(hour=14)),
    ]
    selected = select_covered_bid_points_for_cycle_viewer(points)
    assert [p.bid_minor for p in selected] == [30_000, 10_000]


def test_bid_point_viewer_page_count() -> None:
    assert bid_point_viewer_page_count(0) == 0
    assert bid_point_viewer_page_count(1) == 1
    assert bid_point_viewer_page_count(10) == 1
    assert bid_point_viewer_page_count(11) == 2


def test_clamp_bid_point_page_edges() -> None:
    assert clamp_bid_point_page(-1, 3) == 0
    assert clamp_bid_point_page(0, 3) == 0
    assert clamp_bid_point_page(2, 3) == 2
    assert clamp_bid_point_page(9, 3) == 2
    assert clamp_bid_point_page(0, 0) == 0


def test_render_bid_point_viewer_shows_up_to_ten_lines_per_page() -> None:
    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    points = [
        replace(
            _point(20_000 + i * 100, impressions=1000 + i, is_covered=True, at=base),
            carts=10 + i,
            spend=100.0 + i,
            cart_cpa=10.0,
        )
        for i in range(12)
    ]
    page0 = render_bid_point_viewer_message(0, points, page_size=10)
    assert page0.count("₽: показы") == 10
    assert "Страница 1 / 2" in page0
    page1 = render_bid_point_viewer_message(1, points, page_size=10)
    assert page1.count("₽: показы") == 2
    assert "Страница 2 / 2" in page1


def test_render_bid_point_viewer_zero_carts_shows_dash_cpa() -> None:
    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    point = _point(35_000, impressions=2500, is_covered=True, at=base)
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    assert "корзины 0" in text
    assert "CPA корзины — ₽" in text


def test_bid_point_viewer_keyboard_has_prev_and_next_pages() -> None:
    packed_prev = AutoShelfBidControlBidPoints(
        adv_setting_original_id=42,
        index=0,
    ).pack()
    packed_next = AutoShelfBidControlBidPoints(
        adv_setting_original_id=42,
        index=2,
    ).pack()
    keyboard = build_bid_point_viewer_keyboard(42, page=1, total_points=25, page_size=10)
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert packed_prev in callbacks
    assert packed_next in callbacks


def test_auto_shelf_bid_control_bid_points_callback_roundtrip() -> None:
    original = AutoShelfBidControlBidPoints(adv_setting_original_id=99, index=2)
    restored = AutoShelfBidControlBidPoints.unpack(original.pack())
    assert restored.adv_setting_original_id == 99
    assert restored.index == 2
