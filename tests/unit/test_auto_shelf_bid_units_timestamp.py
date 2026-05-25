"""Unit-тесты форматирования меток времени для Telegram."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    format_timestamp_for_telegram,
    truncate_datetime_to_seconds,
)

pytestmark = pytest.mark.unit


def test_truncate_datetime_to_seconds() -> None:
    ts = datetime(2026, 5, 25, 12, 49, 50, 204349, tzinfo=timezone.utc)
    assert truncate_datetime_to_seconds(ts).microsecond == 0


def test_format_timestamp_for_telegram_datetime_converts_utc_to_msk() -> None:
    ts = datetime(2026, 5, 25, 12, 49, 50, 204349, tzinfo=timezone.utc)
    assert format_timestamp_for_telegram(ts) == "2026-05-25 15:49:50 МСК"


def test_format_timestamp_for_telegram_string_with_fraction() -> None:
    assert format_timestamp_for_telegram("2026-05-25 12:49:50.204349") == (
        "2026-05-25 15:49:50 МСК"
    )
