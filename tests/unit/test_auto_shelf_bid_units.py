"""Unit-тесты контракта единиц ставок auto_shelf bid control."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    format_bid_minor_for_telegram,
    resolve_test_segment_start_utc,
    rubles_to_bid_minor,
    wb_min_cpm_rub_to_bid_minor,
)
from app.core.mp.wb.dto import AdvMinNmidsBids

pytestmark = pytest.mark.unit


def test_wb_min_cpm_rub_to_bid_minor_converts_rubles() -> None:
    assert wb_min_cpm_rub_to_bid_minor(120) == 12_000
    assert wb_min_cpm_rub_to_bid_minor(200) == 20_000


def test_resolve_wb_min_bid_minor_from_adv_min_nmids_bids() -> None:
    min_bids = AdvMinNmidsBids(auto={10749810: 120}, search={})
    assert AutoShelfBidControlManager.resolve_wb_min_bid_minor(min_bids, 10749810) == 12_000


def test_resolve_wb_min_bid_minor_fallback_when_missing() -> None:
    assert AutoShelfBidControlManager.resolve_wb_min_bid_minor(None, 10749810) == 10_000


def test_format_bid_minor_for_telegram() -> None:
    assert format_bid_minor_for_telegram(20_000) == "200 ₽"
    assert format_bid_minor_for_telegram(100) == "1 ₽"
    assert format_bid_minor_for_telegram(None) == "—"


def test_rubles_to_bid_minor() -> None:
    assert rubles_to_bid_minor(500) == 50_000


def test_resolve_test_segment_start_prefers_test_started_at() -> None:
    test_at = datetime(2026, 5, 25, 14, 0, 0, tzinfo=timezone.utc)
    cycle_at = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    assert (
        resolve_test_segment_start_utc(
            test_started_at=test_at,
            current_cycle_started_at=cycle_at,
        )
        == test_at
    )


def test_resolve_test_segment_start_falls_back_to_cycle() -> None:
    cycle_at = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    assert (
        resolve_test_segment_start_utc(
            test_started_at=None,
            current_cycle_started_at=cycle_at,
        )
        == cycle_at
    )


def test_resolve_test_segment_start_uses_fallback_now() -> None:
    now = datetime(2026, 5, 25, 16, 0, 0, tzinfo=timezone.utc)
    assert (
        resolve_test_segment_start_utc(
            test_started_at=None,
            current_cycle_started_at=None,
            fallback_now=now,
        )
        == now
    )
