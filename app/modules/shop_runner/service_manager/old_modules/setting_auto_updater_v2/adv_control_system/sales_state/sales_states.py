"""
Состояние	Цель	Действие
OVERSPEND	снизить расход	отключаем ключи, понижаем ставки, повышаем экспоненту
UNDERPERFORM	нарастить продажи	повышаем ставки, добавляем ключи
STABLE	снизить себестоимость без потери заказов	плавное уменьшение ставок
OPTIMAL	удерживать результат	ничего не делаем
None	пауза или нет данных	ждём обновлений



"""

from enum import Enum, auto

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)


class SalesStates(Enum):
    OVERSPEND = auto()  # Снизить расход
    UNDERPERFORM = auto()  # Нарастить продажи
    STABLE = auto()  # Снизить себестоимость без потери заказов
    OPTIMAL = auto()  # Удерживать результат


def detect_campaign_state(plan: PlanData, fact: FactData) -> SalesStates | None:
    """Определяет состояние кампании adv по плану и факту.

    Args:
        plan: Плановые показатели кампании
        fact: Фактические показатели кампании

    Returns:
        Состояние кампании или None, если данных недостаточно
    """
    # OVERSPEND: перерасход — расходы выше максимума
    if fact.pay_for_order > plan.max_pay_for_order:
        return SalesStates.OVERSPEND

    # UNDERPERFORM: недопродажи — продаж меньше плана
    if (
        fact.predict_orders < plan.orders
        and fact.pay_for_order < plan.max_pay_for_order
    ):
        return SalesStates.UNDERPERFORM

    # План выполнен
    if fact.predict_orders >= plan.orders:
        # STABLE: себестоимость выше целевой
        if fact.pay_for_order > plan.target_pay_for_order:
            return SalesStates.STABLE
        # OPTIMAL: всё в норме
        return SalesStates.OPTIMAL

    # Если данных недостаточно
    return None
