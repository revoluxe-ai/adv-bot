"""Unit-тесты SSOT CPO: orders_per_cart, smoothing, точка CH."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    V3_KEY_CART_TO_ORDER_PRIOR_CARTS,
    conv_views_to_orders_at_ch_point,
    load_rec_orders_per_view_for_v3,
    order_cpo_at_ch_point,
    orders_per_cart_from_wb_carts_per_order_ratio,
    resolve_orders_per_cart_for_cpo,
    smooth_key_orders_per_cart,
)


@pytest.mark.unit
def test_orders_per_cart_from_wb_ratio() -> None:
    assert orders_per_cart_from_wb_carts_per_order_ratio(4.0) == 0.25
    assert orders_per_cart_from_wb_carts_per_order_ratio(None) is None


@pytest.mark.unit
def test_same_bid_different_cart_conv_different_cpo() -> None:
    opc = 0.2
    cpo_low = order_cpo_at_ch_point(
        bid=510.0, conv_carts_to_views=0.0006, orders_per_cart=opc
    )
    cpo_high = order_cpo_at_ch_point(
        bid=510.0, conv_carts_to_views=0.0153, orders_per_cart=opc
    )
    assert cpo_low is not None and cpo_high is not None
    assert cpo_low > cpo_high
    assert conv_views_to_orders_at_ch_point(
        conv_carts_to_views=0.0153, orders_per_cart=opc
    ) == pytest.approx(0.00306)


@pytest.mark.unit
def test_smooth_key_carts_zero_returns_campaign() -> None:
    campaign = 0.1
    assert (
        smooth_key_orders_per_cart(
            campaign_orders_per_cart_7d=campaign,
            key_orders=5,
            key_carts=0,
        )
        == campaign
    )


@pytest.mark.unit
def test_smooth_campaign_none_returns_none() -> None:
    assert (
        smooth_key_orders_per_cart(
            campaign_orders_per_cart_7d=None,
            key_orders=3,
            key_carts=10,
        )
        is None
    )
    assert resolve_orders_per_cart_for_cpo(
        campaign_orders_per_cart_7d=None,
        key_orders=3,
        key_carts=10,
    ) is None


@pytest.mark.unit
def test_smooth_key_orders_gt_carts_clamps_and_debug(caplog: pytest.LogCaptureFixture) -> None:
    """WB-окно orders > carts: не падаем, clamp <= 1.0, debug log."""
    campaign = 0.05
    with caplog.at_level(logging.DEBUG):
        result = smooth_key_orders_per_cart(
            campaign_orders_per_cart_7d=campaign,
            key_orders=20,
            key_carts=5,
            prior_carts=5,
        )
    assert result is not None
    assert result <= 1.0
    # blend: (0.05*5+20)/(5+5) = 20.25/10 > 1
    assert result == 1.0
    assert "key_orders > key_carts" in caplog.text


@pytest.mark.unit
def test_smooth_prior_blend() -> None:
    campaign = 0.10
    smoothed = smooth_key_orders_per_cart(
        campaign_orders_per_cart_7d=campaign,
        key_orders=8,
        key_carts=5,
        prior_carts=100,
    )
    assert smoothed == pytest.approx((0.10 * 100 + 8) / (100 + 5))


@pytest.mark.unit
def test_smooth_negative_counts_clamped() -> None:
    smoothed = smooth_key_orders_per_cart(
        campaign_orders_per_cart_7d=0.2,
        key_orders=-3,
        key_carts=-1,
    )
    assert smoothed == 0.2


@pytest.mark.unit
def test_example_calculation_cpo_at_point() -> None:
    """Числовой пример из плана: campaign 0.10, 8/5 carts, prior 100."""
    campaign = 0.10
    smoothed = smooth_key_orders_per_cart(
        campaign_orders_per_cart_7d=campaign,
        key_orders=8,
        key_carts=5,
        prior_carts=V3_KEY_CART_TO_ORDER_PRIOR_CARTS,
    )
    assert smoothed == pytest.approx(18.0 / 105)
    conv_order = conv_views_to_orders_at_ch_point(
        conv_carts_to_views=0.015,
        orders_per_cart=smoothed,
    )
    assert conv_order == pytest.approx(0.015 * (18.0 / 105))
    cpo = order_cpo_at_ch_point(
        bid=510.0,
        conv_carts_to_views=0.015,
        orders_per_cart=smoothed,
    )
    assert cpo is not None and cpo > 0


@pytest.mark.asyncio
async def test_load_rec_orders_per_view_for_v3_returns_none_when_guarded() -> None:
    adv = SimpleNamespace(adv_id=777, auto_shelf_bid_control_enabled=True)
    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.is_auto_campaign_active",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.modules.shop_runner.wb_stat_manager.rec_conversion_service.get_rec_conversion",
        new=AsyncMock(return_value=0.42),
    ) as get_rec_conversion_mock:
        result = await load_rec_orders_per_view_for_v3(
            adv,
            rec_system_promotion_mode_active=True,
        )

    assert result is None
    get_rec_conversion_mock.assert_not_awaited()
