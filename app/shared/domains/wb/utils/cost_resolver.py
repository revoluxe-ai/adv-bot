"""Общая логика определения целевой себестоимости заказа."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeGuard

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
        PipelineContext,
    )
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
        PlanFactSummary,
    )


def resolve_target_cost_from_context(ctx: PipelineContext) -> float | None:
    """Определяет целевую себестоимость заказа в зависимости от выполнения плана.

    Логика выбора:
    - Если план по заказам выполнен (fact.predict_orders >= plan.orders)
      → возвращаем plan.target_pay_for_order
    - Иначе → возвращаем plan.max_pay_for_order

    Args:
        ctx: Контекст выполнения с планом и фактом

    Returns:
        Целевая себестоимость заказа или None если данные невалидны
    """
    try:
        if not ctx.plan or not ctx.fact:
            return None

        # Логика выбора target/max в зависимости от выполнения плана
        if ctx.fact.predict_orders >= ctx.plan.orders:
            return ctx.plan.target_pay_for_order
        return ctx.plan.max_pay_for_order

    except (AttributeError, TypeError):
        return None


def _is_real_number(value: object) -> TypeGuard[int | float]:
    """True для int/float, не bool (bool — подкласс int)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _resolve_target_cost_pair(
    plan_orders: int | None,
    plan_target_pay_for_order: int | float | None,
    plan_max_pay_for_order: int | float | None,
    fact_predict_orders: float | None,
) -> tuple[float, Literal["target", "max"]] | None:
    """Единая валидация и ветвление: (себестоимость, какой порог) или None.

    ``resolve_target_cost`` и ``resolve_target_cost_threshold_kind`` — тонкие
    обёртки; вызывающим кодам, нужным оба значения, использовать
    ``resolve_target_cost_and_threshold_kind``.
    """
    if not (
        _is_real_number(plan_orders)
        and _is_real_number(plan_target_pay_for_order)
        and _is_real_number(plan_max_pay_for_order)
    ):
        return None
    plan_o = float(plan_orders)
    plan_t = float(plan_target_pay_for_order)
    plan_m = float(plan_max_pay_for_order)
    if fact_predict_orders is None:
        fact_orders = 0.0
    elif not _is_real_number(fact_predict_orders):
        return None
    else:
        fact_orders = float(fact_predict_orders)
    if fact_orders >= plan_o:
        return (plan_t, "target")
    return (plan_m, "max")


def resolve_target_cost(
    plan_orders: int | None,
    plan_target_pay_for_order: int | float | None,
    plan_max_pay_for_order: int | float | None,
    fact_predict_orders: float | None,
) -> float | None:
    """Определяет целевую себестоимость заказа по скалярам плана и факта.

    Логика выбора:
    - Если план по заказам выполнен (fact_predict_orders >= plan_orders)
      → возвращаем plan_target_pay_for_order
    - Иначе → возвращаем plan_max_pay_for_order

    Args:
        plan_orders: План по заказам.
        plan_target_pay_for_order: Целевая себестоимость при выполнении плана.
        plan_max_pay_for_order: Максимальная себестоимость при невыполнении плана.
        fact_predict_orders: Факт/прогноз заказов (None трактуется как 0.0).

    Returns:
        Целевая себестоимость заказа или None если данные невалидны.
    """
    pair = _resolve_target_cost_pair(
        plan_orders,
        plan_target_pay_for_order,
        plan_max_pay_for_order,
        fact_predict_orders,
    )
    return pair[0] if pair else None


def resolve_target_cost_threshold_kind(
    plan_orders: int | None,
    plan_target_pay_for_order: int | float | None,
    plan_max_pay_for_order: int | float | None,
    fact_predict_orders: float | None,
) -> Literal["target", "max"] | None:
    """Какой порог применён при том же правиле, что и ``resolve_target_cost``."""
    pair = _resolve_target_cost_pair(
        plan_orders,
        plan_target_pay_for_order,
        plan_max_pay_for_order,
        fact_predict_orders,
    )
    return pair[1] if pair else None


def resolve_target_cost_and_threshold_kind(
    plan_orders: int | None,
    plan_target_pay_for_order: int | float | None,
    plan_max_pay_for_order: int | float | None,
    fact_predict_orders: float | None,
) -> tuple[float, Literal["target", "max"]] | None:
    """Себестоимость и вид порога одним проходом (см. ``resolve_target_cost``)."""
    return _resolve_target_cost_pair(
        plan_orders,
        plan_target_pay_for_order,
        plan_max_pay_for_order,
        fact_predict_orders,
    )


def resolve_target_cost_from_summary(
    summary: PlanFactSummary | None,
    *,
    plan_orders: int | None,
    plan_target_pay_for_order: int | float | None,
    plan_max_pay_for_order: int | float | None,
) -> float | None:
    """Определяет целевую себестоимость заказа из факта + актуального плана.

    Факт/прогноз заказов берётся из ``PlanFactSummary`` (CH-кеш), а значения
    плана/target/max передаются отдельно из текущих настроек AdvSetting/PlanData.

    Args:
        summary: Сводка план-факт или None (используется только ``fact_predict_orders``)
        plan_orders: Текущий план заказов
        plan_target_pay_for_order: Текущая целевая себестоимость
        plan_max_pay_for_order: Текущая максимальная себестоимость

    Returns:
        Целевая себестоимость заказа или None если данные невалидны
    """
    if not summary:
        return None
    return resolve_target_cost(
        plan_orders,
        plan_target_pay_for_order,
        plan_max_pay_for_order,
        summary.fact_predict_orders,
    )
