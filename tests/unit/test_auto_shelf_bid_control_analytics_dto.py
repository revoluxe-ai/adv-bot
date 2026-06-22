"""Unit-тесты производных метрик BidStatsDTO."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)

pytestmark = pytest.mark.unit


def test_build_bid_stats_dto_cart_cpa_slot_is_cpc_even_with_zero_clicks() -> None:
    """Поле cart_cpa = +inf для UI при zero-click строке; best-bid SQL отсекает clicks=0."""
    dto = AutoShelfBidControlAnalyticsRepository._build_bid_stats_dto(
        {
            "bid_minor": 31_000,
            "currency": "RUB",
            "mode": None,
            "last_interval_at": None,
            "impressions": 100,
            "clicks": 0,
            "carts": 0,
            "orders": 0,
            "spend": 330.43,
        }
    )
    assert dto.cart_cpa == float("inf")


def test_build_bid_stats_dto_score_matches_cpc() -> None:
    dto = AutoShelfBidControlAnalyticsRepository._build_bid_stats_dto(
        {
            "bid_minor": 20_000,
            "currency": "RUB",
            "mode": None,
            "last_interval_at": None,
            "impressions": 1000,
            "clicks": 10,
            "carts": 57,
            "orders": 0,
            "spend": 2006.50,
        }
    )
    assert dto.cart_cpa == pytest.approx(2006.50 / 10)
