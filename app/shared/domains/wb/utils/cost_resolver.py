"""Общая логика определения целевой себестоимости заказа."""

from __future__ import annotations

from typing import TYPE_CHECKING

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


def resolve_target_cost_from_summary(summary: PlanFactSummary | None) -> float | None:
    """Определяет целевую себестоимость заказа из PlanFactSummary.

    Логика выбора:
    - Если план по заказам выполнен (fact_predict_orders >= plan_orders)
      → возвращаем plan_target_pay_for_order
    - Иначе → возвращаем plan_max_pay_for_order

    Args:
        summary: Сводка план-факт или None

    Returns:
        Целевая себестоимость заказа или None если данные невалидны
    """
    if not summary:
        return None

    # Проверяем наличие необходимых полей
    if (
        summary.plan_orders is None
        or summary.plan_target_pay_for_order is None
        or summary.plan_max_pay_for_order is None
    ):
        return None

    fact_orders = summary.fact_predict_orders or 0.0

    # Логика выбора target/max в зависимости от выполнения плана
    if fact_orders >= summary.plan_orders:
        return summary.plan_target_pay_for_order
    return summary.plan_max_pay_for_order
