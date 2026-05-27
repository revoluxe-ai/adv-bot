"""Build MIN_CPA / OPTIMUM / MAX_CONVERSION candidates from a position profile.

``predicted_cpa`` в ``ModeCandidate`` — прогноз **себестоимости заказа** (руб.), та же
шкала, что у ``CalculatedKeyword.pay_for_order``:
``pay_for_order_at_point = bid_at_point / (conv_views_to_orders_keyword * 1000)``.
Используется ``bid`` точки профиля и ``conv_views_to_orders`` **ключа** (V2). В точке
профиля хранится ``conv_carts_to_views`` (корзины), но себестоимость заказа считается
по конверсии заказов ключа — иначе прогноз CPO будет занижен пропорционально
``carts_to_orders``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)

if TYPE_CHECKING:
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
        CalculatedKeyword,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )


def _finite_pay(row: PositionProfilePoint) -> float | None:
    if row.pay_for_cart is None:
        return None
    if math.isinf(row.pay_for_cart):
        return None
    return float(row.pay_for_cart)


def resolve_effective_state_cost(
    *,
    profile_cost: float | None,
    keyword_pay_for_order: float | None,
    worst_cost: float | None,
    allow_worst_imputation: bool,
) -> tuple[float, bool]:
    """Единая логика state_cost: прогноз профиля → факт ключа → worst-imputation.

    Прогноз профиля уже учитывает ``conv_views_to_orders`` ключа, поэтому возвращаем его
    напрямую. ``pay_for_order`` ключа — fallback, когда профиля нет (нет точки M/O/C).
    """
    if profile_cost is not None:
        return float(profile_cost), False
    if keyword_pay_for_order is not None:
        return float(keyword_pay_for_order), False
    if allow_worst_imputation and worst_cost is not None:
        return float(worst_cost), True
    return float("inf"), False


def predicted_pay_for_order_from_point(
    row: PositionProfilePoint,
    *,
    conv_views_to_orders: float | None,
) -> float | None:
    """Себестоимость заказа на позиции в шкале ``CalculatedKeyword.pay_for_order``.

    ``CPO = bid / (conv_views_to_orders * 1000)`` — V2 формула с ``conv_views_to_orders``
    **ключа** (а не ``conv_carts_to_views`` точки, которая считает только корзины).
    """
    if conv_views_to_orders is None or conv_views_to_orders <= 0 or row.bid <= 0:
        return None
    orders = calc_orders_per_1000_rub(float(conv_views_to_orders), float(row.bid))
    if orders is None:
        return None
    return calc_pay_for_order(orders)


def build_mode_candidates(
    *,
    profile: list[PositionProfilePoint] | None,
    keyword_text: str,
    conv_views_to_orders: float | None = None,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Return three mode candidates; invalid if profile missing or unusable.

    ``conv_views_to_orders`` — конверсия показ→заказ ключа (V2), нужна для прогноза CPO.
    Без неё ``predicted_cpa`` будет ``None`` и режимы пометятся как invalid.
    """
    empty = {
        m: ModeCandidate(
            mode=m,
            is_valid=False,
            invalid_reason="no_position_profile",
        )
        for m in AggressionTargetMode
    }
    if not profile:
        return empty

    usable = [p for p in profile if p.predicted_conversion is not None and p.bid >= 0]
    if not usable:
        return {
            m: ModeCandidate(
                mode=m,
                is_valid=False,
                invalid_reason="no_conversion_points",
            )
            for m in AggressionTargetMode
        }

    def _pfo(row: PositionProfilePoint) -> float | None:
        return predicted_pay_for_order_from_point(
            row,
            conv_views_to_orders=conv_views_to_orders,
        )

    # MIN_CPA: минимальный CPO по профилю при текущей ``conv_views_to_orders`` ключа
    pfo_rows = [(p, _pfo(p)) for p in usable if _pfo(p) is not None]
    if not pfo_rows:
        min_cpa = ModeCandidate(
            mode=AggressionTargetMode.MIN_CPA,
            is_valid=False,
            invalid_reason="no_keyword_conv_views_to_orders",
        )
    else:
        best_min, best_pfo = min(pfo_rows, key=lambda t: float(t[1] or 0.0))
        min_cpa = ModeCandidate(
            mode=AggressionTargetMode.MIN_CPA,
            bid=float(best_min.bid),
            position=best_min.position,
            predicted_conversion=best_min.predicted_conversion,
            predicted_cpa=best_pfo,
            economy_score=-float(best_pfo or 0.0),
            is_valid=True,
        )

    # MAX_CONVERSION: точка с максимальной conv_carts_to_views (топ), CPO на её ставке
    best_conv = max(usable, key=lambda p: float(p.predicted_conversion or 0.0))
    max_pfo = _pfo(best_conv)
    max_conv = ModeCandidate(
        mode=AggressionTargetMode.MAX_CONVERSION,
        bid=float(best_conv.bid),
        position=best_conv.position,
        predicted_conversion=best_conv.predicted_conversion,
        predicted_cpa=max_pfo,
        conversion_score=float(best_conv.predicted_conversion or 0.0),
        is_valid=max_pfo is not None,
        invalid_reason=None if max_pfo is not None else "no_keyword_conv_views_to_orders",
    )

    # OPTIMUM: баланс conv/pay (по корзинам — для выбора позиции), CPO на её ставке
    def optimum_score(p: PositionProfilePoint) -> float:
        conv = float(p.predicted_conversion or 0.0)
        pay = _finite_pay(p)
        if pay is None or pay <= 0:
            return -1.0
        return conv / (1.0 + pay)

    best_opt = max(usable, key=optimum_score)
    opt_score = optimum_score(best_opt)
    opt_pfo = _pfo(best_opt)
    optimum = ModeCandidate(
        mode=AggressionTargetMode.OPTIMUM,
        bid=float(best_opt.bid),
        position=best_opt.position,
        predicted_conversion=best_opt.predicted_conversion,
        predicted_cpa=opt_pfo,
        conversion_score=float(best_opt.predicted_conversion or 0.0),
        economy_score=opt_score,
        is_valid=opt_score > 0 and opt_pfo is not None,
        invalid_reason=(
            None
            if opt_score > 0 and opt_pfo is not None
            else (
                "optimum_score_non_positive"
                if opt_score <= 0
                else "no_keyword_conv_views_to_orders"
            )
        ),
    )

    _ = keyword_text  # reserved for logging
    return {
        AggressionTargetMode.MIN_CPA: min_cpa,
        AggressionTargetMode.OPTIMUM: optimum,
        AggressionTargetMode.MAX_CONVERSION: max_conv,
    }

def stored_strategy_mode(kw: CalculatedKeyword) -> KeywordStrategyMode:
    return kw.keyword_setting.strategy_mode
