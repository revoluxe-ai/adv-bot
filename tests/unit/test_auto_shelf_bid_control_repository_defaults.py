from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    DEFAULT_CURRENCY,
    DEFAULT_TARGET_TEST_IMPRESSIONS,
    DEFAULT_TARGET_TEST_OBSERVATION_MINUTES,
    DEFAULT_TEST_SHARE,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    DEFAULT_MAX_BID_MINOR,
    DEFAULT_MIN_BID_DISTANCE_MINOR,
)

import pytest

pytestmark = pytest.mark.unit


def test_auto_shelf_default_settings_constants() -> None:
    """Product-дефолты: *_minor в копейках (500 ₽ max, шаг 1 ₽)."""
    assert DEFAULT_MAX_BID_MINOR == 50_000
    assert DEFAULT_CURRENCY == "RUB"
    assert DEFAULT_MIN_BID_DISTANCE_MINOR == 100
    assert DEFAULT_TARGET_TEST_IMPRESSIONS == 500
    assert DEFAULT_TARGET_TEST_OBSERVATION_MINUTES == 60
    assert DEFAULT_TEST_SHARE == 0.1
