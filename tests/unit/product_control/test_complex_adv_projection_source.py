"""Adapter: ComplexAdv → ComplexAdvProjectionSource (read-only)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.product_control.application.projection.sources import (
    complex_adv_to_projection_source,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.complex_adv import (
    ComplexAdv,
)

pytestmark = pytest.mark.unit


def _adv_setting(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "id": 1,
        "adv_id": 100,
        "nmids": [1],
        "search_adv_id": None,
        "wb_cabinet": SimpleNamespace(shop_id="from-cabinet"),
        "plan_for_sales_for_day": None,
        "target_price_for_order": None,
        "max_price_for_order": None,
        "strategy": None,
        "auto_update_strategy": None,
        "target_position_mode": None,
        "min_target_position": None,
        "individual_keywords_target_place_mode": None,
        "bidder_mode": None,
        "auto_update_white_list": False,
        "bidder_active": False,
        "bidder_coroutine_type": None,
        "bidder_step": 1,
        "hard_min_ctr": None,
        "rec_system_mode": False,
        "auto_shelf_bid_control_enabled": False,
        "auto_update_target_place": False,
        "keyword_calibration_max_step": 1,
        "active_status": "started",
        "bot_active": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_complex_adv_source_uses_search_object_physical_adv_id() -> None:
    auto = _adv_setting(search_adv_id=8888, nmids=[5])
    search = _adv_setting(id=2, adv_id=200, nmids=[5])
    complex_adv = ComplexAdv(auto, search, shop_id="shop-x")
    source = complex_adv_to_projection_source(complex_adv)
    assert source.shop_id == "shop-x"
    assert source.search_leg is not None
    assert source.search_leg.physical_adv_id == 200
    assert source.search_linkage_adv_id == 8888
