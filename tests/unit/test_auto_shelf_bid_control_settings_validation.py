"""Unit tests for AutoShelfBidControlSettings validation."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
)


pytestmark = pytest.mark.unit


def test_target_test_observation_minutes_rejects_less_than_hour() -> None:
    settings = AutoShelfBidControlSettings(
        nmid=1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
        target_test_impressions=500,
        target_test_observation_minutes=60,
        test_share=0.1,
    )

    with pytest.raises(ValueError):
        settings.target_test_observation_minutes = 30


def test_target_test_observation_minutes_accepts_hour_and_more() -> None:
    settings = AutoShelfBidControlSettings(
        nmid=1,
        max_bid_minor=50_000,
        min_bid_distance_minor=100,
        target_test_impressions=500,
        target_test_observation_minutes=60,
        test_share=0.1,
    )

    assert settings.target_test_observation_minutes == 60
