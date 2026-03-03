"""Единая точка расчёта «заказов на 1000₽» и себестоимости заказа.

CPM = стоимость за 1000 показов (руб.). За 1000 ₽ получаем 1_000_000/CPM показов.
Заказов на 1000₽ = (показы с 1000₽) × conv = (1_000_000/CPM) × conv = conv × 1_000_000/CPM.
Себестоимость заказа (руб.) = 1000 / orders_per_1000_rub.
"""


def calc_orders_per_1000_rub(conv_views_to_orders: float, cpm: float | None) -> float | None:
    """Заказов на 1000 руб. рекламы при данной конверсии и CPM.

    CPM — руб. за 1000 показов. При CPM <= 0 возвращает 0.
    """
    if cpm is None or cpm <= 0:
        return None
    return conv_views_to_orders * 1_000_000.0 / cpm


def calc_pay_for_order(orders_per_1000_rub: float, spend: float) -> float:
    """Себестоимость одного заказа (руб.). CPO = 1000 / orders_per_1000_rub."""
    if orders_per_1000_rub == 0:
        return spend
    return 1000.0 / orders_per_1000_rub
