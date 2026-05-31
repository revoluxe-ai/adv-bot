"""Build MIN_CPA / OPTIMUM / MAX_CONVERSION candidates from a position profile.

``predicted_cpa`` — CPO заказа на точке CH (руб.):
``к→к`` точки × (корзина→заказ РК за 7 дней из ``wb_common_stat``) → conv показ→заказ
на ставке → ``calc_pay_for_order``. SSOT: ``v3_point_order_cpo``.

OPTIMUM: ``select_optimum_row_production`` — balance conv/economy на всём usable-профиле.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    aggression_target_for_stored_mode,
)
from app.modules.shop_runner.service_manager.services.v3_optimum_balance import (
    select_optimum_row_production,
)
from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    conv_views_to_orders_at_ch_point,
    order_cpo_at_ch_point,
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


def _pay_for_cart_at_point(row: PositionProfilePoint) -> float | None:
    """Руб/корзина на точке CH для отображения в UI (зависит от корзинной conv)."""
    pay = row.pay_for_cart
    if pay is None or not math.isfinite(pay):
        return None
    value = float(pay)
    return value if value > 0 else None


def resolve_effective_state_cost(
    *,
    profile_cost: float | None,
    worst_cost: float | None,
    allow_worst_imputation: bool = True,
) -> tuple[float, bool]:
    """Единая логика state_cost CH-tier: профиль → per-mode worst → ``inf``.

    ``profile_cost`` — CPO из CH-матрицы для конкретного режима M/O/C. Если его нет,
    подставляется ``worst_cost`` по этому же режиму (пессимистичный CPA РК), без gate
    «вся матрица invalid». Fallback на ``keyword.pay_for_order`` не используется.

    Args:
        allow_worst_imputation: если ``False``, worst не подставляется (legacy call sites).
    """
    if profile_cost is not None:
        return float(profile_cost), False
    if allow_worst_imputation and worst_cost is not None:
        return float(worst_cost), True
    return float("inf"), False


def predicted_pay_for_order_from_point(
    row: PositionProfilePoint,
    *,
    conv_views_to_orders: float | None,
    rk_orders_per_cart: float | None = None,
) -> float | None:
    """CPO заказа на точке: CH ``к→к`` + RK корзина→заказ или legacy conv ключа."""
    if rk_orders_per_cart is not None and rk_orders_per_cart > 0:
        return order_cpo_at_ch_point(
            bid=float(row.bid),
            conv_carts_to_views=row.predicted_conversion,
            rk_orders_per_cart=rk_orders_per_cart,
        )
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
    rk_orders_per_cart: float | None = None,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Return three mode candidates; invalid if profile missing or unusable.

    Usable — только ``ch_observed=True`` (реальные buckets CH). Синтетика
    ``_fill_positions`` не участвует в M/O/C (см. ``BidPositionRow.ch_observed``).

    ``rk_orders_per_cart`` — заказов на корзину РК (7 дней, ``wb_common_stat``), SSOT CPO.
    ``conv_views_to_orders`` — только legacy/fallback, если RK ratio не задан.
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

    usable = [
        p
        for p in profile
        if p.predicted_conversion is not None
        and p.bid >= 0
        and p.ch_observed
    ]
    if not usable:
        return {
            m: ModeCandidate(
                mode=m,
                is_valid=False,
                invalid_reason="no_conversion_points",
            )
            for m in AggressionTargetMode
        }

    use_rk = rk_orders_per_cart is not None and rk_orders_per_cart > 0

    def _pfo(row: PositionProfilePoint) -> float | None:
        return predicted_pay_for_order_from_point(
            row,
            conv_views_to_orders=conv_views_to_orders,
            rk_orders_per_cart=rk_orders_per_cart if use_rk else None,
        )

    def _orders_per_view(row: PositionProfilePoint) -> float | None:
        if not use_rk:
            return None
        return conv_views_to_orders_at_ch_point(
            conv_carts_to_views=row.predicted_conversion,
            rk_orders_per_cart=rk_orders_per_cart,
        )

    def _with_orders_per_view(
        mc: ModeCandidate,
        row: PositionProfilePoint,
    ) -> ModeCandidate:
        opv = _orders_per_view(row)
        if opv is None:
            return mc
        return mc.model_copy(update={"predicted_orders_per_view": opv})

    # MIN_CPA: минимальный CPO по профилю (на точке CH × RK корзина→заказ)
    pfo_rows: list[tuple[PositionProfilePoint, float]] = []
    for p in usable:
        cpo = _pfo(p)
        if cpo is None:
            continue
        pfo_rows.append((p, cpo))
    if not pfo_rows:
        min_cpa = ModeCandidate(
            mode=AggressionTargetMode.MIN_CPA,
            is_valid=False,
            invalid_reason=(
                "no_rk_conv_carts_to_orders"
                if use_rk
                else "no_keyword_conv_views_to_orders"
            ),
        )
    else:
        best_min, best_pfo = min(pfo_rows, key=lambda t: float(t[1] or 0.0))
        min_cpa = _with_orders_per_view(
            ModeCandidate(
                mode=AggressionTargetMode.MIN_CPA,
                bid=float(best_min.bid),
                position=best_min.position,
                predicted_conversion=best_min.predicted_conversion,
                predicted_cpa=best_pfo,
                pay_for_cart=_pay_for_cart_at_point(best_min),
                economy_score=-float(best_pfo or 0.0),
                is_valid=True,
            ),
            best_min,
        )

    # MAX_CONVERSION: точка с максимальной conv_carts_to_views (топ), CPO на её ставке
    best_conv = max(usable, key=lambda p: float(p.predicted_conversion or 0.0))
    max_pfo = _pfo(best_conv)
    max_conv = _with_orders_per_view(
        ModeCandidate(
            mode=AggressionTargetMode.MAX_CONVERSION,
            bid=float(best_conv.bid),
            position=best_conv.position,
            predicted_conversion=best_conv.predicted_conversion,
            predicted_cpa=max_pfo,
            pay_for_cart=_pay_for_cart_at_point(best_conv),
            conversion_score=float(best_conv.predicted_conversion or 0.0),
            is_valid=max_pfo is not None,
            invalid_reason=(
                None
                if max_pfo is not None
                else (
                    "no_rk_conv_carts_to_orders"
                    if use_rk
                    else "no_keyword_conv_views_to_orders"
                )
            ),
        ),
        best_conv,
    )

    # OPTIMUM: balance conv/economy на всём usable-профиле
    opt_rows = [
        (p, float(p.predicted_conversion or 0.0), float(cpo))
        for p, cpo in pfo_rows
    ]
    opt_pick = select_optimum_row_production(opt_rows)
    if opt_pick is None:
        optimum = ModeCandidate(
            mode=AggressionTargetMode.OPTIMUM,
            is_valid=False,
            invalid_reason=(
                "no_rk_conv_carts_to_orders"
                if use_rk
                else "no_keyword_conv_views_to_orders"
            ),
        )
    else:
        best_opt = opt_pick.row
        opt_pfo = opt_pick.cpo
        optimum = _with_orders_per_view(
            ModeCandidate(
                mode=AggressionTargetMode.OPTIMUM,
                bid=float(best_opt.bid),
                position=best_opt.position,
                predicted_conversion=best_opt.predicted_conversion,
                predicted_cpa=opt_pfo,
                pay_for_cart=_pay_for_cart_at_point(best_opt),
                conversion_score=float(best_opt.predicted_conversion or 0.0),
                economy_score=opt_pick.score,
                is_valid=True,
            ),
            best_opt,
        )

    return {
        AggressionTargetMode.MIN_CPA: min_cpa,
        AggressionTargetMode.OPTIMUM: optimum,
        AggressionTargetMode.MAX_CONVERSION: max_conv,
    }

def moc_equality_flags(
    min_cpa: ModeCandidate,
    optimum: ModeCandidate,
    max_conv: ModeCandidate,
) -> tuple[bool, bool]:
    """Совпадение ступеней лестницы для MOC-stats: ``(o_eq_c, o_eq_m)``.

    Критерий как у effective ladder: только ``target_place`` (``position``),
    без сравнения bid/CPO — см. ``mode_candidates_same_effective_target``.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
        mode_candidates_same_effective_target,
    )

    o_eq_m = mode_candidates_same_effective_target(min_cpa, optimum)
    o_eq_c = mode_candidates_same_effective_target(optimum, max_conv)
    return o_eq_c, o_eq_m


def target_place_for_v3_strategy_mode(
    mode: KeywordStrategyMode,
    candidates: dict[AggressionTargetMode, ModeCandidate],
) -> int | None:
    """``target_place`` для биддера: позиция режима из ``build_mode_candidates``.

    Для OFF вызывающий код должен подставить прокси ``MIN_CPA`` (как в sync).
    """
    agg = aggression_target_for_stored_mode(mode)
    if agg is None:
        return None
    cand = candidates.get(agg)
    if cand is None or not cand.is_valid or cand.position is None:
        return None
    return max(1, int(cand.position))


def mode_for_v3_target_place(mode: KeywordStrategyMode) -> KeywordStrategyMode:
    """Режим для расчёта ``target_place``: OFF → MIN_CPA (нет кандидата OFF)."""
    if mode == KeywordStrategyMode.OFF:
        return KeywordStrategyMode.MIN_CPA
    return mode


def resolve_v3_target_place(
    strategy_mode: KeywordStrategyMode,
    candidates: dict[AggressionTargetMode, ModeCandidate],
) -> int | None:
    """``target_place`` ключа по ``strategy_mode`` и лестнице V3."""
    return target_place_for_v3_strategy_mode(
        mode_for_v3_target_place(strategy_mode),
        candidates,
    )


def stored_strategy_mode(kw: CalculatedKeyword) -> KeywordStrategyMode:
    return kw.keyword_setting.strategy_mode
