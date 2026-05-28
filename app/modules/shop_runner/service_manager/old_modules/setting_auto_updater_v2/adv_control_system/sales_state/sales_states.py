"""
Состояние	Цель	Действие
OVERSPEND	снизить расход	отключаем ключи, понижаем ставки, повышаем экспоненту
UNDERPERFORM	нарастить продажи	повышаем ставки, добавляем ключи
STABLE	снизить себестоимость без потери заказов	плавное уменьшение ставок
OPTIMAL	удерживать результат	ничего не делаем
NO_DATA (Н)	нет данных plan/fact	ключи: target_place=0, MIN_CPA
None	пауза (битый план)	ждём обновлений



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
    NO_DATA = auto()  # Н — нет данных для plan/fact (V3: MIN_CPA + target_place 0)


# При недовыполнении плана: pay в [90%; max] — стабилизация (OPTIMAL), не рост ключей.
# Совпадает с порогом M3 headroom в V3 (``plan_headroom_plus_one``).
MAX_PAY_STABILIZATION_RATIO = 0.9


def detect_campaign_state(plan: PlanData, fact: FactData) -> SalesStates | None:
    """Определяет состояние кампании adv по плану и факту.

    Args:
        plan: Плановые показатели кампании
        fact: Фактические показатели кампании

    Returns:
        Состояние кампании или None, если данных недостаточно
    """
    if not any(
        [
            plan.target_pay_for_order,
            plan.orders,
            plan.max_pay_for_order,
        ]
    ):
        return None

    if fact.pay_for_order is None:
        return SalesStates.NO_DATA

    # OVERSPEND: перерасход — расходы выше максимума
    if fact.pay_for_order > plan.max_pay_for_order:
        return SalesStates.OVERSPEND

    if fact.predict_orders < plan.orders:
        max_pfo = float(plan.max_pay_for_order)
        pay = float(fact.pay_for_order)
        stabilization_floor = MAX_PAY_STABILIZATION_RATIO * max_pfo
        # 90–100% от max при недопродажах: удержание, без добавления/снятия ключей (OPTIMAL)
        if pay >= stabilization_floor:
            return SalesStates.OPTIMAL
        return SalesStates.UNDERPERFORM

    # План выполнен
    if fact.predict_orders >= plan.orders:
        # STABLE: себестоимость выше целевой
        if fact.pay_for_order > plan.target_pay_for_order:
            return SalesStates.STABLE
        # OPTIMAL: всё в норме
        return SalesStates.OPTIMAL

    return None
