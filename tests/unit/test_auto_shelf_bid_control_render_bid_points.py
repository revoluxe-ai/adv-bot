"""Unit-тесты просмотрщика покрытых ставок цикла в Telegram."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.client_bot.user_interface.views.callbacks import AutoShelfBidControlBidPoints
from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    build_bid_point_viewer_keyboard,
    clamp_bid_point_index,
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


def test_clamp_bid_point_index_edges() -> None:
    assert clamp_bid_point_index(-1, 3) == 0
    assert clamp_bid_point_index(0, 3) == 0
    assert clamp_bid_point_index(2, 3) == 2
    assert clamp_bid_point_index(9, 3) == 2
    assert clamp_bid_point_index(0, 0) == 0


def test_render_bid_point_viewer_same_line_format_as_main_screen() -> None:
    from tests.unit.test_auto_shelf_bid_control_render_message import _view_with_bid_point

    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    covered = _point(20_000, impressions=23848, is_covered=True, at=base)
    covered = replace(
        covered,
        carts=124,
        spend=4646.77,
        cart_cpa=37.47,
    )
    view = replace(
        _view_with_bid_point(),
        cycle_covered_points_count=3,
        cycle_bid_points=[covered],
    )
    text = render_bid_point_viewer_message(view, 1, [covered, covered, covered])
    assert "Покрытые ставки (текущий цикл):" in text
    assert (
        "200 ₽: показы 23848, корзины 124, расход 4646.77 ₽, CPA корзины 37.47 ₽"
        in text
    )
    assert "2 / 3" in text


def test_bid_point_viewer_keyboard_has_prev_and_next() -> None:
    packed_prev = AutoShelfBidControlBidPoints(
        adv_setting_original_id=42,
        index=0,
    ).pack()
    packed_next = AutoShelfBidControlBidPoints(
        adv_setting_original_id=42,
        index=2,
    ).pack()
    keyboard = build_bid_point_viewer_keyboard(42, index=1, total=3)
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
