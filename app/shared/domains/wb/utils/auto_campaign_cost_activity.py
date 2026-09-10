"""Единое решение об активности автокампании по среднему и total CPO vs resolve.

Кампания считается неактивной только при подтверждённом нарушении:
``avg_cost > resolve`` и ``fact_pay_for_order > resolve``. При нормальном
``avg_cost`` total CPO не требуется. При высоком ``avg_cost`` без плохого total
CPO результат остаётся неопределённым.

Promobonus overlay
------------------
Порог ``resolve`` берётся из ``PlanFactProvider.get_effective_plan_data``, а не
из сырых колонок Plan в PG. Overlay нужен, когда ``raise_plan_on_promobonuses``
включён и есть usable ``promo_fraction`` (``f`` → ``M = 1/(1-f)``).

Как fraction попадает в расчёт (приоритет):

1. Явный аргумент ``complex_adv`` у ``get_auto_campaign_cost_activity_metrics`` /
   ``is_auto_campaign_active`` — единственный надёжный путь (keywords, Telegram
   menu, v3 rec-gate, shelf-mode).
2. Уже пришитый ``promo_fraction`` / ``effective_promo_plan`` на самом
   ``AdvSetting``.

Без того и другого порог — сырой Plan (``M=1``). Стек вызовов не читается:
локаль ``complex_adv`` у caller сама по себе overlay не включает.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state import (
    SalesStates,
    detect_campaign_state,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    fact_data_from_plan_fact_summary,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost_and_threshold_kind,
)
from app.shared.domains.wb.utils.promo_overlay import (
    attach_overlay_fields,
    overlay_for_adv,
)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


def _as_finite_cost_number(value: object) -> float | None:
    """Finite ``int``/``float`` → ``float``; ``bool``, ``NaN``, inf, прочее → None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    return result


def _resolve_cost_activity(
    *,
    target_cost: object,
    avg_cost: object,
    fact_pay_for_order: object,
) -> bool | None:
    """Tri-state cost-rule: не гасить кампанию только по высокому среднему CPO.

    Returns:
        ``True``: ``avg_cost <= target`` (total CPO не смотрим).
        ``False``: ``avg_cost > target`` и ``fact_pay_for_order > target``.
        ``None``: нет валидных чисел либо avg плохой, а total ещё не подтвердил
        нарушение.
    """
    target_cost_value = _as_finite_cost_number(target_cost)
    avg_cost_value = _as_finite_cost_number(avg_cost)
    if target_cost_value is None or avg_cost_value is None:
        return None
    if avg_cost_value <= target_cost_value:
        return True

    fact_pay_for_order_value = _as_finite_cost_number(fact_pay_for_order)
    if fact_pay_for_order_value is None:
        return None
    if fact_pay_for_order_value > target_cost_value:
        return False
    return None


def _plan_fact_summary_has_finite_fact_data(plan_fact_summary: object) -> bool:
    """Достаточно ли finite fact-полей, чтобы считать ``campaign_sales_state``."""
    fact_predict_orders = getattr(plan_fact_summary, "fact_predict_orders", None)
    if _as_finite_cost_number(fact_predict_orders) is None:
        return False
    fact_original_orders = getattr(plan_fact_summary, "fact_original_orders", None)
    if (
        fact_original_orders is not None
        and _as_finite_cost_number(fact_original_orders) is None
    ):
        return False
    fact_pay_for_order = getattr(plan_fact_summary, "fact_pay_for_order", None)
    return (
        fact_pay_for_order is None
        or _as_finite_cost_number(fact_pay_for_order) is not None
    )


@dataclass(frozen=True)
class AutoCampaignCostActivityMetrics:
    """Снимок cost-rule: порог, средний CPO, tri-state и sales-state.

    ``target_cost`` уже с runtime overlay, если fraction доехал до
    ``get_effective_plan_data``. ``plan_set`` — есть ли Plan (сырой или overlay).
    """

    target_cost: float | None
    avg_cost: float | None
    is_active: bool | None
    plan_set: bool  # True if plan (orders/target/max) is present for this adv
    plan_fact_ch_ts_msk: str | None
    cost_threshold_kind: Literal["target", "max"] | None
    campaign_sales_state: SalesStates | None = None
    fact_pay_for_order: float | None = None


def _promo_fraction_from_object(carrier: object | None) -> Decimal | None:
    """Извлечь ненулевой promo fraction с ComplexAdv / EffectivePromoPlan / DTO.

    Смотрит ``promo_fraction``, затем ``fraction``. ``None`` / ``0`` / битый
    каст → ``None`` (overlay не применяется).
    """
    if carrier is None:
        return None
    raw = getattr(carrier, "promo_fraction", None)
    if raw is None:
        raw = getattr(carrier, "fraction", None)
    if raw in (None, 0, Decimal("0")):
        return None
    try:
        return Decimal(str(raw))
    except Exception:
        return None


def _resolve_runtime_complex_adv(
    adv_setting: AdvSetting,
    complex_adv: object | None,
) -> object | None:
    """Носитель overlay для ``get_effective_plan_data`` без подмены base Plan.

    Приоритет: явный ``complex_adv`` → ``adv_setting.promo_fraction`` →
    ``adv_setting.effective_promo_plan``. ``None`` означает сырой Plan (M=1).
    """
    if complex_adv is not None:
        return complex_adv
    promo_fraction = _promo_fraction_from_object(adv_setting)
    if promo_fraction is not None:
        return adv_setting
    effective_promo_plan = getattr(adv_setting, "effective_promo_plan", None)
    effective_fraction = _promo_fraction_from_object(effective_promo_plan)
    if effective_fraction is not None:
        from types import SimpleNamespace

        return SimpleNamespace(promo_fraction=effective_fraction)
    return None


def _ensure_adv_overlay_attached(
    adv_setting: AdvSetting,
    *,
    complex_adv: object | None,
) -> None:
    """Пришить runtime overlay на ``AdvSetting`` (не трогает persisted Plan).

    Fraction: аргумент ``complex_adv``, иначе уже лежащий
    ``adv_setting.promo_fraction``. Стек не читается. Без fraction — no-op.
    Побочный эффект: мутирует ``promo_fraction`` / ``promo_multiplier`` /
    ``effective_promo_plan`` на ``adv_setting``.
    """
    fraction = _promo_fraction_from_object(complex_adv)
    if fraction is None:
        fraction = _promo_fraction_from_object(adv_setting)
    if fraction is None:
        return
    overlay = overlay_for_adv(adv_setting, fraction=fraction)
    attach_overlay_fields(
        adv_setting,
        overlay,
        adv_id=getattr(adv_setting, "adv_id", None),
    )


async def get_auto_campaign_cost_activity_metrics(
    adv_setting: AdvSetting,
    *,
    plan_fact_reader: PlanFactReader | None = None,
    days_for_avg: int = 7,
    complex_adv: object | None = None,
) -> AutoCampaignCostActivityMetrics:
    """Собрать порог/средний CPO и tri-state ``is_active``.

    Overlay применяется, если передан ``complex_adv`` **или** на setting уже
    есть ``promo_fraction`` (флаг ON). Стек caller не читается.

    Args:
        adv_setting: настройки РК.
        plan_fact_reader: снимок plan-fact; по умолчанию ``PlanFactReader()``.
        days_for_avg: окно среднего CPO (дни).
        complex_adv: носитель ``promo_fraction``; ``None`` — сырой Plan, если
        fraction не пришит на setting.

    Returns:
        ``AutoCampaignCostActivityMetrics``; ``is_active`` — ``bool | None``.
    """
    reader = plan_fact_reader or PlanFactReader()
    if complex_adv is not None:
        _ensure_adv_overlay_attached(adv_setting, complex_adv=complex_adv)
    elif getattr(adv_setting, "raise_plan_on_promobonuses", False) is True:
        _ensure_adv_overlay_attached(adv_setting, complex_adv=None)
    runtime_complex_adv = _resolve_runtime_complex_adv(adv_setting, complex_adv)
    plan = PlanFactProvider.get_effective_plan_data(
        adv_setting,
        complex_adv=runtime_complex_adv,
    )
    plan_fact_summary = await reader.get_latest_plan_fact(adv_setting.adv_id)

    cost_threshold_kind: Literal["target", "max"] | None = None
    fact_predict_orders = (
        plan_fact_summary.fact_predict_orders
        if plan_fact_summary is not None
        else None
    )
    fact_predict_orders_value = _as_finite_cost_number(fact_predict_orders)
    if (
        plan is None
        or plan_fact_summary is None
        or fact_predict_orders_value is None
    ):
        target_cost = None
    else:
        resolved = resolve_target_cost_and_threshold_kind(
            plan.orders,
            plan.target_pay_for_order,
            plan.max_pay_for_order,
            fact_predict_orders_value,
        )
        if resolved is None:
            target_cost = None
            cost_threshold_kind = None
        else:
            target_cost, cost_threshold_kind = resolved
            target_cost = _as_finite_cost_number(target_cost)
            if target_cost is None:
                cost_threshold_kind = None
    avg_cost = await full_wb_adv_stat.get_additional_cost_per_order_for_adv(
        adv_setting.adv_id,
        days=days_for_avg,
    )
    avg_cost = _as_finite_cost_number(avg_cost)
    ch_ts = (
        plan_fact_summary.plan_fact_ch_ts_msk
        if plan_fact_summary is not None
        else None
    )
    fact_pay_for_order = (
        plan_fact_summary.fact_pay_for_order
        if plan_fact_summary is not None
        else None
    )
    fact_pay_for_order_value = _as_finite_cost_number(fact_pay_for_order)
    is_active = _resolve_cost_activity(
        target_cost=target_cost,
        avg_cost=avg_cost,
        fact_pay_for_order=fact_pay_for_order_value,
    )

    campaign_sales_state: SalesStates | None = None
    if (
        plan is not None
        and plan_fact_summary is not None
        and _plan_fact_summary_has_finite_fact_data(plan_fact_summary)
    ):
        fact = fact_data_from_plan_fact_summary(plan_fact_summary, adv_setting)
        if fact is not None:
            campaign_sales_state = detect_campaign_state(plan, fact)

    return AutoCampaignCostActivityMetrics(
        target_cost=target_cost,
        avg_cost=avg_cost,
        is_active=is_active,
        plan_set=plan is not None,
        plan_fact_ch_ts_msk=ch_ts,
        cost_threshold_kind=cost_threshold_kind,
        campaign_sales_state=campaign_sales_state,
        fact_pay_for_order=fact_pay_for_order_value,
    )


async def is_auto_campaign_active(
    adv_setting: AdvSetting,
    *,
    plan_fact_reader: PlanFactReader | None = None,
    days_for_avg: int = 7,
    complex_adv: object | None = None,
) -> bool | None:
    """Tri-state активность автокампании по cost-rule (обёртка над metrics).

    Считает полный снимок через ``get_auto_campaign_cost_activity_metrics`` и
    возвращает только ``is_active``. Overlay — только через ``complex_adv=``
    или уже пришитый fraction на setting.

    Returns:
        ``True`` / ``False`` / ``None`` — см. ``_resolve_cost_activity``.
    """
    metrics = await get_auto_campaign_cost_activity_metrics(
        adv_setting,
        plan_fact_reader=plan_fact_reader,
        days_for_avg=days_for_avg,
        complex_adv=complex_adv,
    )
    return metrics.is_active
