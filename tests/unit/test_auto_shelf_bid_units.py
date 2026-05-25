"""Unit-тесты контракта единиц ставок auto_shelf bid control."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    format_bid_minor_for_telegram,
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


def test_format_bid_minor_for_telegram() -> None:
    assert format_bid_minor_for_telegram(20_000) == "200 ₽"
    assert format_bid_minor_for_telegram(100) == "1 ₽"
    assert format_bid_minor_for_telegram(None) == "—"


def test_rubles_to_bid_minor() -> None:
    assert rubles_to_bid_minor(500) == 50_000
