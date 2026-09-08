"""Применение cached promo overlay к AdvSetting / DTO без мутации базового Plan."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.modules.auto_budget_manager.promo_state_service import log_effective_promo_entities
from app.modules.auto_budget_manager.redis_promo_state_manager import CachedShopPromoState
from app.modules.plan_fact.provider import PlanFactProvider
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost
from app.shared.domains.wb.utils.promo_plan_multiplier import (
    EffectivePromoPlan,
)


def fraction_from_cached_state(
    state: CachedShopPromoState | None,
    *adv_ids: int | None,
) -> Decimal:
    """Фактическая f по OR auto/search. Stale/untrusted/miss → 0."""
    if state is None or state.is_stale or not state.overlay_trusted:
        return Decimal("0")
    best = Decimal("0")
    for adv_id in adv_ids:
        if adv_id is None:
            continue
        campaign = state.campaigns.get(int(adv_id))
        if campaign is None or not campaign.usable:
            continue
        if campaign.effective_fraction > best:
            best = campaign.effective_fraction
    return best


def overlay_for_adv(
    adv: Any,
    *,
    fraction: Decimal,
) -> EffectivePromoPlan:
    """Построить overlay для AdvSetting."""
    return PlanFactProvider.get_effective_promo_plan(adv, fraction=fraction)


def attach_overlay_fields(
    target: Any,
    overlay: EffectivePromoPlan,
    *,
    adv_id: int | None = None,
) -> None:
    """Записать runtime overlay на DTO. Не трогает persisted Plan columns."""
    target.promo_fraction = overlay.fraction
    target.promo_multiplier = overlay.multiplier
    target.effective_promo_plan = overlay
    if overlay.active and adv_id is not None:
        log_effective_promo_entities(adv_id=adv_id, overlay=overlay)


def _fact_predict_orders_from_complex_adv(complex_adv: Any) -> float | None:
    """Взять только факт заказов, не подменяя его spend-CPO."""
    fact_predict_orders = getattr(complex_adv, "fact_predict_orders", None)
    if fact_predict_orders is not None:
        return fact_predict_orders
    plan_fact_summary = getattr(complex_adv, "plan_fact_summary", None)
    if plan_fact_summary is None:
        return None
    return getattr(plan_fact_summary, "fact_predict_orders", None)


def _resolve_runtime_cpo(
    complex_adv: Any,
    overlay: EffectivePromoPlan,
) -> float | None:
    """Разрешить CPO по active overlay либо по базовым колонкам AdvSetting."""
    adv_setting = complex_adv.adv_setting
    if overlay.active and overlay.plan is not None:
        plan_orders = overlay.plan.orders
        target_pay_for_order = overlay.plan.target_pay_for_order
        max_pay_for_order = overlay.plan.max_pay_for_order
    else:
        plan_orders = getattr(adv_setting, "plan_for_sales_for_day", None)
        target_pay_for_order = getattr(adv_setting, "target_price_for_order", None)
        max_pay_for_order = getattr(adv_setting, "max_price_for_order", None)
    return resolve_target_cost(
        plan_orders,
        target_pay_for_order,
        max_pay_for_order,
        _fact_predict_orders_from_complex_adv(complex_adv),
    )


def _apply_runtime_resolve_cpo(complex_adv: Any, resolved_cpo: float | None) -> None:
    """Синхронизировать baked target/resolve поля одного runtime DTO."""
    apply_method = getattr(complex_adv, "apply_runtime_resolve_cpo", None)
    if callable(apply_method):
        apply_method(resolved_cpo)
        return
    # Lightweight DTOs in unit seams may not expose the production helper.
    setattr(complex_adv, "_target_pay_for_order", resolved_cpo)
    setattr(complex_adv, "_resolve_cpo", resolved_cpo)
    for name in ("target_pay_for_order", "resolve_cpo"):
        try:
            setattr(complex_adv, name, resolved_cpo)
        except (AttributeError, TypeError):
            pass


def apply_cached_state_to_complex_adv(
    complex_adv: Any,
    state: CachedShopPromoState | None,
) -> EffectivePromoPlan:
    """Применить свежий Redis overlay к уже построенному ``ComplexAdv``.

    ``get_complex_advs`` обычно читает Redis до watchdog refresh. После
    успешного refresh этот helper обновляет тот же DTO в текущем тике, чтобы
    budget/activity paths не ждали следующего запуска. При miss/stale
    ``fraction_from_cached_state`` возвращает ноль и оставляет безопасный
    ``M=1``.

    Args:
        complex_adv: DTO кампании с ``adv_setting``, ``adv_id`` и
            ``search_adv_id``.
        state: snapshot Redis, полученный после refresh; может быть ``None``.

    Returns:
        Построенный effective promo plan.
    """
    adv_setting = complex_adv.adv_setting
    fraction = fraction_from_cached_state(
        state,
        getattr(complex_adv, "adv_id", None),
        getattr(complex_adv, "search_adv_id", None),
    )
    overlay = overlay_for_adv(adv_setting, fraction=fraction)
    attach_overlay_fields(
        adv_setting,
        overlay,
        adv_id=getattr(complex_adv, "adv_id", None),
    )
    complex_adv.promo_fraction = overlay.fraction
    complex_adv.promo_multiplier = overlay.multiplier
    complex_adv.effective_promo_plan = overlay
    _apply_runtime_resolve_cpo(
        complex_adv,
        _resolve_runtime_cpo(complex_adv, overlay),
    )
    return overlay
