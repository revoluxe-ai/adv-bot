"""Unit-тесты SSOT CPO на точке CH × корзина→заказ РК."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    conv_views_to_orders_at_ch_point,
    order_cpo_at_ch_point,
    orders_per_cart_from_wb_carts_per_order_ratio,
)


@pytest.mark.unit
def test_orders_per_cart_from_wb_ratio() -> None:
    assert orders_per_cart_from_wb_carts_per_order_ratio(4.0) == 0.25
    assert orders_per_cart_from_wb_carts_per_order_ratio(None) is None


@pytest.mark.unit
def test_same_bid_different_cart_conv_different_cpo() -> None:
    rk = 0.2
    cpo_low = order_cpo_at_ch_point(
        bid=510.0, conv_carts_to_views=0.0006, rk_orders_per_cart=rk
    )
    cpo_high = order_cpo_at_ch_point(
        bid=510.0, conv_carts_to_views=0.0153, rk_orders_per_cart=rk
    )
    assert cpo_low is not None and cpo_high is not None
    assert cpo_low > cpo_high
    assert conv_views_to_orders_at_ch_point(
        conv_carts_to_views=0.0153, rk_orders_per_cart=rk
    ) == pytest.approx(0.00306)
