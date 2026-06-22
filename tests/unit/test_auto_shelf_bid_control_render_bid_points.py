"""Unit-тесты просмотрщика ставок цикла в Telegram."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

import app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render as render_module
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
    CoverageLayerBidDTO,
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


def _coverage_point(
    bid_minor: int,
    *,
    impressions: int,
    valid_hours: int,
    closed_layers: int,
    undercovered: bool,
    expected_daily_impressions: float | None = None,
    expected_daily_clicks: float | None = None,
    expected_daily_orders: float | None = None,
    expected_order_cost_rub: float | None = None,
    plan_distance_score: float | None = None,
    status_text: str | None = None,
    label: str = "bid",
) -> CoverageLayerBidDTO:
    """Собрать строку coverage-view со всеми forecast-полями."""
    return CoverageLayerBidDTO(
        label=label,
        bid_minor=bid_minor,
        impressions=impressions,
        valid_hours=valid_hours,
        closed_layers=closed_layers,
        undercovered=undercovered,
        expected_daily_impressions=expected_daily_impressions,
        expected_daily_clicks=expected_daily_clicks,
        expected_daily_orders=expected_daily_orders,
        expected_order_cost_rub=expected_order_cost_rub,
        plan_distance_score=plan_distance_score,
        status_text=status_text,
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


def test_select_cycle_bid_points_for_viewer_zero_click_cpc_goes_last() -> None:
    base = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    points = [
        _point(10_000, impressions=600, is_covered=True, at=base, clicks=10, cart_cpa=30.0),
        _point(20_000, impressions=600, is_covered=True, at=base.replace(hour=14), clicks=0, cart_cpa=float("inf")),
        _point(30_000, impressions=600, is_covered=True, at=base.replace(hour=16), clicks=12, cart_cpa=10.0),
    ]
    selected = select_cycle_bid_points_for_viewer(points, optimization_metric=OptimizationMetric.CPC)
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
    points = [
        CoverageLayerBidDTO(
            label="bid",
            bid_minor=20_000 + i * 100,
            impressions=1000 + i,
            valid_hours=10 + i,
            closed_layers=1 if i % 2 == 0 else 0,
            undercovered=(i % 2 != 0),
        )
        for i in range(12)
    ]
    page0 = render_bid_point_viewer_message(0, points, page_size=10)
    header = "Покрытие ставок теста:"
    legend = "✅ closed_layers > current_layer"
    assert header in page0
    assert legend in page0
    assert page0.count("₽: показы") == 10
    assert "Страница 1 / 2" in page0
    page1 = render_bid_point_viewer_message(1, points, page_size=10)
    assert page1.count("₽: показы") == 2
    assert "Страница 2 / 2" in page1


def test_render_bid_point_viewer_later_pages_keep_zero_coverage_rows() -> None:
    points = [
        CoverageLayerBidDTO(
            label="best_plan_bid_minor" if i == 0 else "bid",
            bid_minor=20_000 + i * 100,
            impressions=100 if i < 10 else 0,
            valid_hours=1 if i < 10 else 0,
            closed_layers=1 if i < 10 else 0,
            undercovered=(i >= 10),
            is_best_plan=(i == 0),
        )
        for i in range(12)
    ]
    page1 = render_bid_point_viewer_message(1, points, page_size=10)
    assert "Страница 2 / 2" in page1
    assert "показы 0, валидные часы 0, closed_layers 0" in page1


def test_render_bid_point_viewer_status_and_best_markers() -> None:
    point = CoverageLayerBidDTO(
        label="bid",
        bid_minor=35_000,
        impressions=2500,
        valid_hours=12,
        closed_layers=0,
        undercovered=True,
        is_best_plan=True,
        is_selected_next_test=True,
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    header = "Покрытие ставок теста:"
    assert text.startswith(header)
    assert "⏳ 🎯 ⭐️ 350 ₽" in text
    assert "показы 2500" in text
    assert "валидные часы 12" in text
    assert "closed_layers 0" in text


def test_render_bid_point_viewer_shows_compact_labels() -> None:
    point = CoverageLayerBidDTO(
        label="current_main_bid_minor / current_test_bid_minor",
        bid_minor=20_000,
        impressions=10,
        valid_hours=1,
        closed_layers=0,
        undercovered=True,
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    assert "[current_main_bid_minor / current_test_bid_minor]" in text


def test_render_bid_point_viewer_uses_passed_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    point = CoverageLayerBidDTO(
        label="bid",
        bid_minor=20_000,
        impressions=10,
        valid_hours=1,
        closed_layers=0,
        undercovered=True,
    )
    monkeypatch.setattr(
        render_module,
        "format_bid_minor_for_telegram",
        lambda value, currency: f"{value}:{currency}",
    )
    text = render_bid_point_viewer_message(0, [point], currency="KZT", page_size=10)
    assert "20000:KZT" in text


def test_render_bid_point_viewer_shows_closed_status() -> None:
    point = CoverageLayerBidDTO(
        label="bid",
        bid_minor=20_000,
        impressions=165,
        valid_hours=9,
        closed_layers=3,
        undercovered=False,
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    assert "✅ 200 ₽" in text


def test_render_bid_point_viewer_shows_forecast_and_status() -> None:
    point = _coverage_point(
        20_500,
        impressions=165,
        valid_hours=9,
        closed_layers=0,
        undercovered=True,
        expected_daily_impressions=54_321.0,
        expected_daily_clicks=1_629.63,
        expected_daily_orders=48.89,
        expected_order_cost_rub=222.2,
        plan_distance_score=0.3,
        status_text="eligible",
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    assert "прогноз показов/сутки: 54 321" in text
    assert "прогноз кликов/сутки: 1 630" in text
    assert "прогноз заказов/сутки: 48.89" in text
    assert "CPO: 222.20 ₽" in text
    assert "score: 0.300" in text
    assert "status: eligible" in text


def test_render_bid_point_viewer_keeps_missing_forecast_as_dash() -> None:
    point = _coverage_point(
        20_500,
        impressions=165,
        valid_hours=9,
        closed_layers=0,
        undercovered=False,
        status_text="covered",
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10)
    assert "прогноз показов/сутки: —" in text
    assert "прогноз кликов/сутки: —" in text
    assert "прогноз заказов/сутки: —" in text
    assert "CPO: —" in text
    assert "status: covered" in text


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


def test_render_bid_point_viewer_shows_coverage_header_for_ctr() -> None:
    """Просмотрщик coverage использует тот же заголовок независимо от метрики."""
    point = CoverageLayerBidDTO(
        label="bid",
        bid_minor=20_000,
        impressions=1000,
        valid_hours=10,
        closed_layers=1,
        undercovered=False,
    )
    text = render_bid_point_viewer_message(0, [point], page_size=10, optimization_metric=OptimizationMetric.CTR)
    header = "Покрытие ставок теста:"
    assert header in text
