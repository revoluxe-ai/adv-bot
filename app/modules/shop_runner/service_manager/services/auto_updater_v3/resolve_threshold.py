"""Resolve-порог V3: target vs max по plan/fact (orchestrator, ApplyManager, tick)."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)


def compute_resolve_cost_threshold(plan: PlanData, fact: FactData) -> float:
    """Вернуть текущий resolve порог: target при выполнении плана, иначе max."""
    if float(fact.predict_orders) >= float(plan.orders):
        return float(plan.target_pay_for_order)
    return float(plan.max_pay_for_order)


def is_resolve_valid(plan: PlanData, resolve: float) -> bool:
    """Проверить, что порог пригоден для state-решений."""
    return float(plan.max_pay_for_order) > 0 and float(resolve) > 0
