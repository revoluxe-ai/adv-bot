"""Unit-тесты просмотрщика ставок цикла в Telegram."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.client_bot.user_interface.views.callbacks import AutoShelfBidControlBidPoints
from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    _bid_point_viewer_header,
    _bid_point_viewer_legend,
    bid_point_viewer_page_count,
    build_bid_point_viewer_keyboard,
    clamp_bid_point_page,
    cycle_bid_coverage_icon,
    render_auto_shelf_bid_control_message,
    render_bid_point_viewer_message,
    select_cycle_bid_points_for_viewer,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    BidPointStatsDTO,
    OptimizationMetric,
)

pytestmark = pytest.mark.unit


def _point(
    bid_minor: int,
    *,
    impressions: int,
    is_covered: bool,
    at: datetime,
    carts: int = 0,
    clicks: int = 0,
    cart_cpa: float | None = None,
    ctr: float | None = None,
    is_best: bool = False,
) -> BidPointStatsDTO:
    resolved_ctr = ctr
    if resolved_ctr is None and impressions > 0:
        resolved_ctr = clicks / impressions
    return BidPointStatsDTO(
        bid_minor=bid_minor,
        currency="RUB",
        last_interval_at=at,
        impressions=impressions,
        clicks=clicks,
        carts=carts,
        orders=0,
        spend=1.0,
        cart_cpa=cart_cpa,
        ctr=resolved_ctr,
        cart_cr=None,
        is_covered=is_covered,
        is_best=is_best,
        is_current_main=False,
        is_current_test=False,
    )


def test_main_screen_has_no_covered_bid_points_block() -> None:
    from tests.unit.test_auto_shelf_bid_control_render_message import _view_with_bid_point

    text = render_auto_shelf_bid_control_message(_view_with_bid_point())
    assert "Покрытые ставки:" not in text
    assert "… ещё" not in text


def test_cycle_bid_coverage_icon() -> None:
    base = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    assert cycle_bid_coverage_icon(_point(10_000, impressions=100, is_covered=True, at=base)) == "✅"
    assert cycle_bid_coverage_icon(_point(10_000, impressions=100, is_covered=False, at=base)) == "⏳"


def test_select_cycle_bid_points_for_viewer_all_with_impressions_sorted_by_cpc() -> None:
    base = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    points = [
        _point(10_000, impressions=600, is_covered=True, at=base, carts=2, cart_cpa=50.0),
        _point(20_000, impressions=100, is_covered=False, at=base.replace(hour=16)),
        _point(30_000, impressions=600, is_covered=True, at=base.replace(hour=14), carts=5, cart_cpa=10.0),
        _point(40_000, impressions=0, is_covered=False, at=base),
    ]
    selected = select_cycle_bid_points_for_viewer(points)
    assert [p.bid_minor for p in selected] == [30_000, 10_000, 20_000]


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
            cart_cpa=10.0 + i,
        )
        for i in range(12)
    ]
    page0 = render_bid_point_viewer_message(0, points, page_size=10)
    header = _bid_point_viewer_header(OptimizationMetric.CPC)
    legend = _bid_point_viewer_legend(OptimizationMetric.CPC)
    assert header in page0
    assert legend in page0
    assert page0.count("₽: показы") == 10
    assert "Страница 1 / 2" in page0
    page1 = render_bid_point_viewer_message(1, points, page_size=10)
    assert page1.count("₽: показы") == 2
    assert "Страница 2 / 2" in page1


def test_render_bid_point_viewer_status_and_best_markers() -> None:
    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    point = _point(
        35_000,
        impressions=2500,
        is_covered=False,
        at=base,
        is_best=True,
        cart_cpa=1.0,
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    header = _bid_point_viewer_header(OptimizationMetric.CPC)
    assert text.startswith(header)
    assert "⏳ ⭐ 350" in text or "⏳⭐" in text.replace(" ", "")
    assert "корзины 0" in text
    assert "клики 0" in text
    assert "CTR 0.00%" in text
    assert "CPC 1.00 ₽" in text


def test_render_bid_point_viewer_shows_ctr_from_clicks_and_impressions() -> None:
    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    point = _point(
        20_000,
        impressions=165,
        clicks=9,
        is_covered=False,
        at=base,
        carts=10,
        cart_cpa=5.69,
        is_best=True,
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    assert "клики 9" in text
    assert "CTR 5.45%" in text


def test_render_bid_point_viewer_covered_shows_checkmark() -> None:
    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    point = _point(20_000, impressions=3000, is_covered=True, at=base, carts=3, cart_cpa=5.0)
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    assert "✅" in text


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


def test_select_cycle_bid_points_sorted_by_ctr_descending() -> None:
    """При метрике CTR сортировка по убыванию CTR (лучший первым)."""
    base = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    points = [
        _point(10_000, impressions=600, is_covered=True, at=base, clicks=12, ctr=0.02),  # CTR 2%
        _point(20_000, impressions=600, is_covered=True, at=base.replace(hour=14), clicks=30, ctr=0.05),  # CTR 5%
        _point(30_000, impressions=600, is_covered=True, at=base.replace(hour=16), clicks=6, ctr=0.01),  # CTR 1%
    ]
    selected = select_cycle_bid_points_for_viewer(points, optimization_metric=OptimizationMetric.CTR)
    # Отсортировано по CTR убыванию: 5%, 2%, 1%
    assert [p.bid_minor for p in selected] == [20_000, 10_000, 30_000]


def test_select_cycle_bid_points_sorted_by_cpc_ascending() -> None:
    """При метрике CPC сортировка по возрастанию CPC (лучший первым)."""
    base = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    points = [
        _point(10_000, impressions=600, is_covered=True, at=base, carts=3, cart_cpa=30.0),  # CPC 30
        _point(20_000, impressions=600, is_covered=True, at=base.replace(hour=14), carts=6, cart_cpa=15.0),  # CPC 15
        _point(30_000, impressions=600, is_covered=True, at=base.replace(hour=16), carts=2, cart_cpa=50.0),  # CPC 50
    ]
    selected = select_cycle_bid_points_for_viewer(points, optimization_metric=OptimizationMetric.CPC)
    # Отсортировано по CPC возрастанию: 15, 30, 50
    assert [p.bid_minor for p in selected] == [20_000, 10_000, 30_000]


def test_bid_point_viewer_header_for_ctr() -> None:
    """Заголовок для CTR метрики."""
    header = _bid_point_viewer_header(OptimizationMetric.CTR)
    assert "сортировка по CTR" in header
    assert "сортировка по CPC" not in header


def test_bid_point_viewer_header_for_cpc() -> None:
    """Заголовок для CPC метрики."""
    header = _bid_point_viewer_header(OptimizationMetric.CPC)
    assert "сортировка по CPC" in header
    assert "сортировка по CTR" not in header


def test_bid_point_viewer_legend_for_ctr() -> None:
    """Легенда для CTR метрики."""
    legend = _bid_point_viewer_legend(OptimizationMetric.CTR)
    assert "лучшая глобальная по CTR" in legend
    assert "лучшая глобальная по CPC" not in legend


def test_render_bid_point_viewer_shows_ctr_header() -> None:
    """Просмотрщик показывает правильный заголовок для CTR."""
    base = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    point = _point(20_000, impressions=1000, is_covered=True, at=base, clicks=50, ctr=0.05)
    text = render_bid_point_viewer_message(0, [point], page_size=10, optimization_metric=OptimizationMetric.CTR)
    header = _bid_point_viewer_header(OptimizationMetric.CTR)
    assert header in text
