"""Unit-тесты ``candidates``: CPO на точке = к→к CH × корзина→заказ РК 7д."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    moc_equality_flags,
    predicted_pay_for_order_from_point,
    resolve_effective_state_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    mode_candidates_same_effective_target,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)
from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    order_cpo_at_ch_point,
)
from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST, sample_profile


@pytest.mark.unit
def test_predicted_cpa_uses_ch_point_times_rk_cart_to_order() -> None:
    """MIN_CPA — минимальный CPO по точкам CH × RK корзина→заказ."""
    prof = sample_profile(min_pay=25.0, high_pay=40.0)
    rk = RK_ORDERS_PER_CART_TEST
    cand = build_mode_candidates(
        profile=prof,
        keyword_text="kw",
        rk_orders_per_cart=rk,
    )
    min_mc = cand[AggressionTargetMode.MIN_CPA]
    assert min_mc.is_valid
    min_point = min(
        prof,
        key=lambda p: order_cpo_at_ch_point(
            bid=float(p.bid),
            conv_carts_to_views=p.predicted_conversion,
            rk_orders_per_cart=rk,
        )
        or float("inf"),
    )
    expected = order_cpo_at_ch_point(
        bid=float(min_point.bid),
        conv_carts_to_views=min_point.predicted_conversion,
        rk_orders_per_cart=rk,
    )
    assert min_mc.predicted_cpa == expected
    assert min_mc.predicted_cpa is not None and min_mc.predicted_cpa > 1.0


@pytest.mark.unit
def test_same_bid_different_point_cpo_with_rk_ratio() -> None:
    """Одна ставка, разный к→к CH → разный CPO при заданном RK ratio."""
    from datetime import UTC, datetime

    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )

    ts = datetime(2024, 1, 1, tzinfo=UTC)
    prof = [
        PositionProfilePoint(position=32, bid=510, predicted_conversion=0.0006, timestamp=ts),
        PositionProfilePoint(position=40, bid=510, predicted_conversion=0.0153, timestamp=ts),
    ]
    rk = 0.2
    cand = build_mode_candidates(profile=prof, keyword_text="kw", rk_orders_per_cart=rk)
    cpo_deep = order_cpo_at_ch_point(
        bid=510.0, conv_carts_to_views=0.0006, rk_orders_per_cart=rk
    )
    cpo_shallow = order_cpo_at_ch_point(
        bid=510.0, conv_carts_to_views=0.0153, rk_orders_per_cart=rk
    )
    assert cpo_deep is not None and cpo_shallow is not None
    assert cpo_deep > cpo_shallow
    assert cand[AggressionTargetMode.MIN_CPA].predicted_cpa == cpo_shallow


@pytest.mark.unit
def test_target_place_for_v3_strategy_mode_matches_candidate_position() -> None:
    """``target_place`` совпадает с ``ModeCandidate.position`` для режима."""
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
        target_place_for_v3_strategy_mode,
    )

    prof = sample_profile(min_pay=25.0, high_pay=40.0)
    cand = build_mode_candidates(
        profile=prof,
        keyword_text="kw",
        rk_orders_per_cart=RK_ORDERS_PER_CART_TEST,
    )
    assert target_place_for_v3_strategy_mode(
        KeywordStrategyMode.MIN_CPA, cand
    ) == cand[AggressionTargetMode.MIN_CPA].position


@pytest.mark.unit
def test_predicted_cpa_invalid_without_keyword_conv() -> None:
    prof = sample_profile()
    cand = build_mode_candidates(profile=prof, keyword_text="kw", conv_views_to_orders=None)
    for mode in AggressionTargetMode:
        mc = cand[mode]
        assert not mc.is_valid
        assert mc.invalid_reason == "no_keyword_conv_views_to_orders"


@pytest.mark.unit
def test_predicted_pay_for_order_from_point_v2_scale() -> None:
    prof = sample_profile()
    pt = prof[0]
    val = predicted_pay_for_order_from_point(pt, conv_views_to_orders=0.02)
    assert val is not None
    assert val == calc_pay_for_order(calc_orders_per_1000_rub(0.02, float(pt.bid)))  # type: ignore[arg-type]


@pytest.mark.unit
def test_moc_equality_flags_uses_target_place_not_bid() -> None:
    """MOC-stats и effective ladder: alias при одном place, разный bid — всё равно eq."""
    min_c = ModeCandidate(
        mode=AggressionTargetMode.MIN_CPA,
        position=40,
        bid=500.0,
        predicted_cpa=10.0,
        is_valid=True,
    )
    opt = ModeCandidate(
        mode=AggressionTargetMode.OPTIMUM,
        position=40,
        bid=999.0,
        predicted_cpa=20.0,
        is_valid=True,
    )
    max_c = ModeCandidate(
        mode=AggressionTargetMode.MAX_CONVERSION,
        position=1,
        bid=10_000.0,
        predicted_cpa=30.0,
        is_valid=True,
    )
    o_eq_c, o_eq_m = moc_equality_flags(min_c, opt, max_c)
    assert o_eq_m
    assert not o_eq_c
    assert mode_candidates_same_effective_target(min_c, opt)
    assert not mode_candidates_same_effective_target(opt, max_c)


@pytest.mark.unit
def test_resolve_effective_state_cost_does_not_fallback_to_keyword_pfo() -> None:
    """При отсутствии профильного CPO используем только worst-imputation или inf."""
    cost, imputed = resolve_effective_state_cost(
        profile_cost=None,
        worst_cost=None,
        allow_worst_imputation=False,
    )
    assert cost == float("inf")
    assert not imputed
