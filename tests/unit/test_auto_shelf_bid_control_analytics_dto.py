"""Unit-тесты производных метрик BidStatsDTO."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)

pytestmark = pytest.mark.unit


def test_build_bid_stats_dto_cart_cpa_uses_one_cart_when_zero() -> None:
    dto = AutoShelfBidControlAnalyticsRepository._build_bid_stats_dto(
        {
            "bid_minor": 31_000,
            "currency": "RUB",
            "mode": None,
            "impressions": 100,
            "clicks": 1,
            "carts": 0,
            "orders": 0,
            "spend": 330.43,
        }
    )
    assert dto.cart_cpa == pytest.approx(330.43)


def test_build_bid_stats_dto_cart_cpa_normal_when_carts_positive() -> None:
    dto = AutoShelfBidControlAnalyticsRepository._build_bid_stats_dto(
        {
            "bid_minor": 20_000,
            "currency": "RUB",
            "mode": None,
            "impressions": 1000,
            "clicks": 10,
            "carts": 57,
            "orders": 0,
            "spend": 2006.50,
        }
    )
    assert dto.cart_cpa == pytest.approx(2006.50 / 57)
