"""CPO заказа на точке CH: conv корзина→показ (профиль) × orders_per_cart (сглаженный по ключу).

Используется в ``build_mode_candidates``, UI и ``PredictKeywordsTargetPlace`` (V3 MIN/OPTIMUM).
Без импорта ``auto_updater_v3`` (избегаем циклов).

На границе WB только ``carts_per_order``; далее везде ``orders_per_cart`` (заказов на корзину).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting

logger = logging.getLogger(__name__)

RK_CART_TO_ORDER_PASS_DAYS = 7

V3_KEY_CART_TO_ORDER_PRIOR_CARTS = 100
"""Сила prior (в корзинах) для сглаживания key ``orders_per_cart`` к campaign 7d."""


def orders_per_cart_from_wb_carts_per_order_ratio(
    carts_per_order: float | None,
) -> float | None:
    """Заказов на корзину из ``wb_common_stat``: ``SUM(add_to_cart)/SUM(orders)`` → ``1/ratio``."""
    if carts_per_order is None or carts_per_order <= 0:
        return None
    return 1.0 / float(carts_per_order)


def _clamp_non_negative_count(value: int) -> int:
    """Отрицательные counts WB → 0, без исключения."""
    return max(0, int(value))


def smooth_key_orders_per_cart(
    *,
    campaign_orders_per_cart_7d: float | None,
    key_orders: int,
    key_carts: int,
    prior_carts: int = V3_KEY_CART_TO_ORDER_PRIOR_CARTS,
) -> float | None:
    """Сглаженный orders_per_cart ключа: prior к конверсии РК 7d.

    Args:
        campaign_orders_per_cart_7d: baseline РК (заказов на корзину), ``wb_common_stat`` 7d.
        key_orders: заказы ключа за 7d (``CalculatedKeyword.orders``).
        key_carts: корзины ключа за 7d (``CalculatedKeyword.add_to_cart``).
        prior_carts: сила prior в корзинах (MVP: ``V3_KEY_CART_TO_ORDER_PRIOR_CARTS``).

    Returns:
        ``orders_per_cart`` в ``(0, 1]`` или ``None``, если campaign invalid.
    """
    if campaign_orders_per_cart_7d is None or campaign_orders_per_cart_7d <= 0:
        return None

    campaign = min(float(campaign_orders_per_cart_7d), 1.0)
    orders = _clamp_non_negative_count(key_orders)
    carts = _clamp_non_negative_count(key_carts)

    if carts <= 0:
        return campaign if campaign > 0 else None

    prior = max(1, int(prior_carts))
    smoothed = (campaign * prior + float(orders)) / (float(prior) + float(carts))

    if orders > carts:
        pre_clamp = smoothed
        smoothed = min(smoothed, 1.0)
        logger.debug(
            "smooth_key_orders_per_cart: key_orders > key_carts, clamp orders_per_cart "
            "campaign=%.6f key_orders=%s key_carts=%s prior=%s pre_clamp=%.6f smoothed=%.6f",
            campaign,
            orders,
            carts,
            prior,
            pre_clamp,
            smoothed,
        )

    smoothed = min(smoothed, 1.0)
    if smoothed <= 0:
        return None
    return smoothed


def resolve_orders_per_cart_for_cpo(
    *,
    campaign_orders_per_cart_7d: float | None,
    key_orders: int,
    key_carts: int,
    prior_carts: int = V3_KEY_CART_TO_ORDER_PRIOR_CARTS,
) -> float | None:
    """Effective ``orders_per_cart`` для CPO V3 (вне ``LadderInputs`` — sync/predict)."""
    return smooth_key_orders_per_cart(
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        key_orders=key_orders,
        key_carts=key_carts,
        prior_carts=prior_carts,
    )


@dataclass(frozen=True, slots=True)
class KeyOrdersPerCartSnapshot:
    """Метрики корз→заказ для UI профиля V3."""

    campaign_orders_per_cart_7d: float | None
    key_orders_7d: int
    key_carts_7d: int
    key_orders_per_cart_raw: float | None
    key_orders_per_cart_smoothed: float | None
    prior_carts_strength: int


def key_orders_per_cart_snapshot(
    *,
    campaign_orders_per_cart_7d: float | None,
    key_orders: int,
    key_carts: int,
    prior_carts: int = V3_KEY_CART_TO_ORDER_PRIOR_CARTS,
) -> KeyOrdersPerCartSnapshot:
    """Снимок raw/smoothed для карточки ключа."""
    carts = _clamp_non_negative_count(key_carts)
    orders = _clamp_non_negative_count(key_orders)
    raw: float | None = None
    if carts > 0:
        raw = float(orders) / float(carts)
    smoothed = smooth_key_orders_per_cart(
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        key_orders=key_orders,
        key_carts=key_carts,
        prior_carts=prior_carts,
    )
    return KeyOrdersPerCartSnapshot(
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        key_orders_7d=orders,
        key_carts_7d=carts,
        key_orders_per_cart_raw=raw,
        key_orders_per_cart_smoothed=smoothed,
        prior_carts_strength=prior_carts,
    )


def conv_views_to_orders_at_ch_point(
    *,
    conv_carts_to_views: float | None,
    orders_per_cart: float | None = None,
    rk_orders_per_cart: float | None = None,
) -> float | None:
    """Conv показ→заказ на точке: ``к→к`` CH × ``orders_per_cart``."""
    opc = orders_per_cart if orders_per_cart is not None else rk_orders_per_cart
    if conv_carts_to_views is None or conv_carts_to_views <= 0:
        return None
    if opc is None or opc <= 0:
        return None
    return float(conv_carts_to_views) * float(opc)


def order_cpo_at_ch_point(
    *,
    bid: float | None,
    conv_carts_to_views: float | None,
    orders_per_cart: float | None = None,
    rk_orders_per_cart: float | None = None,
) -> float | None:
    """Себестоимость заказа (руб.) на ставке точки CH."""
    if bid is None or bid <= 0:
        return None
    order_conv = conv_views_to_orders_at_ch_point(
        conv_carts_to_views=conv_carts_to_views,
        orders_per_cart=orders_per_cart,
        rk_orders_per_cart=rk_orders_per_cart,
    )
    if order_conv is None:
        return None
    orders = calc_orders_per_1000_rub(order_conv, float(bid))
    if orders is None:
        return None
    return calc_pay_for_order(orders)


async def load_rec_orders_per_view_for_v3(
    adv: AdvSetting,
    *,
    rec_system_promotion_mode_active: bool,
    complex_adv: object | None = None,
) -> float | None:
    """Baseline полок (заказы/показ) для state-level rec_gate — те же условия, что ``above_rec_conversion``.

    Cost-activity получает ``complex_adv`` явно. Без него overlay только если
    fraction уже пришит на ``adv``.

    Returns:
        ``get_rec_conversion`` или ``None``, если правило не применяется (auto campaign inactive и т.д.).
    """
    if not rec_system_promotion_mode_active:
        return None
    from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
        is_auto_campaign_active,
    )
    from app.modules.shop_runner.wb_stat_manager.rec_conversion_service import (
        get_rec_conversion,
    )

    auto_campaign_active = await is_auto_campaign_active(
        adv,
        complex_adv=complex_adv,
    )
    if auto_campaign_active is False:
        return None
    return await get_rec_conversion(adv.adv_id)


async def load_campaign_orders_per_cart_7d(
    adv: AdvSetting,
    *,
    pass_days: int = RK_CART_TO_ORDER_PASS_DAYS,
) -> float | None:
    """Корзина→заказ (orders_per_cart) по nmids РК за ``pass_days`` из ``wb_common_stat``."""
    from app.modules.common_advs_stat.clickhouse_manager import (
        get_cart_to_order_ratio_from_common_items_stat,
    )

    carts_per_order = await get_cart_to_order_ratio_from_common_items_stat(adv, pass_days)
    return orders_per_cart_from_wb_carts_per_order_ratio(carts_per_order)


async def load_rk_orders_per_cart_7d(
    adv: AdvSetting,
    *,
    pass_days: int = RK_CART_TO_ORDER_PASS_DAYS,
) -> float | None:
    """Deprecated alias: ``load_campaign_orders_per_cart_7d``."""
    return await load_campaign_orders_per_cart_7d(adv, pass_days=pass_days)
