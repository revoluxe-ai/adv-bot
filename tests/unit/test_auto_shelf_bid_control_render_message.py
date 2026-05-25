"""Unit-тесты рендера сообщений auto_shelf bid control (единицы в ₽)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    _format_cycle_timestamp,
    render_auto_shelf_bid_control_message,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    BidPointStatsDTO,
)

pytestmark = pytest.mark.unit


def _view_with_bid_point() -> AutoShelfBidControlViewDTO:
    return AutoShelfBidControlViewDTO(
        nmid=10749810,
        auto_adv_id=32824944,
        enabled=True,
        has_settings=True,
        has_state=True,
        dry_run=False,
        bid_units_confirmed=True,
        actual_bid_minor=20_000,
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        current_main_bid_minor=20_000,
        current_test_bid_minor=31_000,
        best_bid_minor=None,
        next_test_bid_minor=31_000,
        currency="RUB",
        current_mode="test",
        current_cycle_started_at=datetime.now(timezone.utc),
        test_started_at=datetime.now(timezone.utc),
        main_started_at=None,
        test_share=0.1,
        target_test_impressions=500,
        target_main_impressions=4500,
        min_bid_distance_minor=100,
        test_impressions=10,
        main_impressions=0,
        covered_points_count=0,
        bid_points_total=1,
        bid_points=[
            BidPointStatsDTO(
                bid_minor=20_000,
                currency="RUB",
                last_interval_at=datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc),
                impressions=100,
                clicks=5,
                carts=2,
                orders=1,
                spend=50.5,
                cart_cpa=25.25,
                ctr=0.05,
                cart_cr=0.4,
                is_covered=False,
                is_best=False,
                is_current_main=True,
                is_current_test=False,
            )
        ],
        last_reason="initialized",
        warnings=[],
    )


def test_format_cycle_timestamp_without_microseconds() -> None:
    ts = datetime(2026, 5, 25, 10, 21, 36, 799753, tzinfo=timezone.utc)
    assert _format_cycle_timestamp(ts) == "2026-05-25 13:21:36 МСК"
    assert ".799753" not in _format_cycle_timestamp(ts)


def test_format_cycle_timestamp_strips_fraction_from_string() -> None:
    assert _format_cycle_timestamp("2026-05-25 12:49:50.204349") == (
        "2026-05-25 15:49:50 МСК"
    )


def test_render_cycle_timestamps_without_fractional_seconds() -> None:
    view = replace(
        _view_with_bid_point(),
        current_cycle_started_at=datetime(
            2026, 5, 25, 10, 21, 36, 799753, tzinfo=timezone.utc
        ),
        test_started_at=datetime(2026, 5, 25, 10, 21, 36, 799753, tzinfo=timezone.utc),
        main_started_at=datetime(
            2026, 5, 25, 12, 11, 12, 448857, tzinfo=timezone.utc
        ),
    )
    text = render_auto_shelf_bid_control_message(view)
    assert "Начат: 2026-05-25 13:21:36 МСК\n" in text
    assert "Тест начат: 2026-05-25 13:21:36 МСК\n" in text
    assert "Main начат: 2026-05-25 15:11:12 МСК\n" in text
    assert ".799753" not in text
    assert ".448857" not in text


def test_render_shows_bid_points_in_rubles_not_raw_kopecks() -> None:
    text = render_auto_shelf_bid_control_message(_view_with_bid_point())
    assert "200 ₽: показы 100" in text
    assert "20000:" not in text
    assert "Минимальная ставка WB: 120 ₽" in text
    assert "Максимальная ставка: 500 ₽" in text
    assert "Шаг между тестовыми ставками: 1 ₽" in text
