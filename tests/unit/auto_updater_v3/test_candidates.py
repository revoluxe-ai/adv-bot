"""Unit-тесты ``candidates``: state_cost = себестоимость заказа (V2-формула).

Прогноз CPO на точке = ``bid_point / (conv_views_to_orders_keyword * 1000)``.
"""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    predicted_pay_for_order_from_point,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)
from tests.unit.auto_updater_v3.conftest import sample_profile


@pytest.mark.unit
def test_predicted_cpa_uses_keyword_conv_views_to_orders_v2_formula() -> None:
    """MIN_CPA берёт минимальный bid из профиля и CPO считает по conv ключа."""
    prof = sample_profile(min_pay=25.0, high_pay=40.0)
    conv = 0.01
    cand = build_mode_candidates(
        profile=prof,
        keyword_text="kw",
        conv_views_to_orders=conv,
    )
    min_mc = cand[AggressionTargetMode.MIN_CPA]
    assert min_mc.is_valid
    min_bid_point = min(prof, key=lambda p: p.bid)
    expected = calc_pay_for_order(calc_orders_per_1000_rub(conv, float(min_bid_point.bid)))  # type: ignore[arg-type]
    assert min_mc.predicted_cpa == expected
    assert min_mc.predicted_cpa is not None and min_mc.predicted_cpa > 1.0


@pytest.mark.unit
def test_predicted_cpa_invalid_without_keyword_conv() -> None:
    prof = sample_profile()
    cand = build_mode_candidates(profile=prof, keyword_text="kw", conv_views_to_orders=None)
    for mode in AggressionTargetMode:
        mc = cand[mode]
        assert not mc.is_valid
        assert mc.invalid_reason in {
            "no_keyword_conv_views_to_orders",
            "optimum_score_non_positive",
        }


@pytest.mark.unit
def test_predicted_pay_for_order_from_point_v2_scale() -> None:
    prof = sample_profile()
    pt = prof[0]
    val = predicted_pay_for_order_from_point(pt, conv_views_to_orders=0.02)
    assert val is not None
    assert val == calc_pay_for_order(calc_orders_per_1000_rub(0.02, float(pt.bid)))  # type: ignore[arg-type]
