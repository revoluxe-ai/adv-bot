from enum import Enum


class OrdersSourceForAutoMode(Enum):
    """Источник заказов для автоуправления рекламой"""

    COMMON_STATISTIC = "COMMON_STATISTIC"  # Общая статистика по товарам
    ADV_SUM = "ADV_SUM"  # По заказам из рекламы
