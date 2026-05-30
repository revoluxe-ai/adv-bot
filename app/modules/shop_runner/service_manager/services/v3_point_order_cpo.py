"""CPO заказа на точке CH: conv корзина→показ (профиль) × conv корзина→заказ (РК, 7 дней).

Используется в ``build_mode_candidates``, UI и ``PredictKeywordsTargetPlace`` (V3 MIN/OPTIMUM).
Без импорта ``auto_updater_v3`` (избегаем циклов).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting

RK_CART_TO_ORDER_PASS_DAYS = 7


def orders_per_cart_from_wb_carts_per_order_ratio(
    carts_per_order: float | None,
) -> float | None:
    """Заказов на корзину из ``wb_common_stat``: ``SUM(add_to_cart)/SUM(orders)`` → ``1/ratio``."""
    if carts_per_order is None or carts_per_order <= 0:
        return None
    return 1.0 / float(carts_per_order)


def conv_views_to_orders_at_ch_point(
    *,
    conv_carts_to_views: float | None,
    rk_orders_per_cart: float | None,
) -> float | None:
    """Conv показ→заказ на точке: ``к→к`` CH × (корзина→заказ РК)."""
    if conv_carts_to_views is None or conv_carts_to_views <= 0:
        return None
    if rk_orders_per_cart is None or rk_orders_per_cart <= 0:
        return None
    return float(conv_carts_to_views) * float(rk_orders_per_cart)


def order_cpo_at_ch_point(
    *,
    bid: float | None,
    conv_carts_to_views: float | None,
    rk_orders_per_cart: float | None,
) -> float | None:
    """Себестоимость заказа (руб.) на ставке точки CH."""
    if bid is None or bid <= 0:
        return None
    order_conv = conv_views_to_orders_at_ch_point(
        conv_carts_to_views=conv_carts_to_views,
        rk_orders_per_cart=rk_orders_per_cart,
    )
    if order_conv is None:
        return None
    orders = calc_orders_per_1000_rub(order_conv, float(bid))
    if orders is None:
        return None
    return calc_pay_for_order(orders)


async def load_rk_orders_per_cart_7d(
    adv: AdvSetting,
    *,
    pass_days: int = RK_CART_TO_ORDER_PASS_DAYS,
) -> float | None:
    """Корзина→заказ по nmids РК за ``pass_days`` из ``wb_common_stat`` (как прогноз продаж)."""
    from app.modules.common_advs_stat.clickhouse_manager import (
        get_cart_to_order_ratio_from_common_items_stat,
    )

    raw = await get_cart_to_order_ratio_from_common_items_stat(adv, pass_days)
    return orders_per_cart_from_wb_carts_per_order_ratio(raw)
