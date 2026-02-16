"""Общая логика расчёта себестоимости заказа из доп. показов (авто-реклама без ключевых слов)."""

from __future__ import annotations


def compute_additional_cost_per_order(
    auto_stat_spend: float,
    auto_stat_orders: int,
    keyword_spend: float,
    keyword_orders: int,
) -> float:
    """Средняя себестоимость заказа из дополнительных показов за период.

    Доп. показы = вся авто-реклама минус траты/заказы по ключевым словам.
    Используется одна и та же формула в common_advs_stat и auto_adv_active_control.

    Формула:
    - addition_spend = max(0, auto_stat_spend - keyword_spend)
    - addition_orders = max(0, auto_stat_orders - keyword_orders) + 1  (+1 избегает деления на 0)
    - return addition_spend / addition_orders

    Args:
        auto_stat_spend: Общий расход авто-рекламы за период.
        auto_stat_orders: Общее число заказов авто-рекламы за период.
        keyword_spend: Расход по ключевым словам за период.
        keyword_orders: Заказы по ключевым словам за период.

    Returns:
        Себестоимость заказа из доп. показов (всегда >= 0, знаменатель не меньше 1).
    """
    addition_spend = max(0.0, auto_stat_spend - keyword_spend)
    addition_orders = max(0, auto_stat_orders - keyword_orders) + 1
    return addition_spend / addition_orders
