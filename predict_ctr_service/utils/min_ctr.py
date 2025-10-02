# Минимальная автономная реализация get_min_ctr для predict_ctr_service
# Возвращает заданный hard_min_ctr если он есть и больше нуля, иначе возвращает безопасный дефолт 0.03
from typing import Any

DEFAULT_MIN_CTR = 0.03


async def get_min_ctr(adv: Any) -> float:
    """Возвращает минимальный CTR для кампании.

    Логика упрощена для автономной работы сервиса:
    - Если у объекта adv есть атрибут `hard_min_ctr` и он не пустой, возвращаем его.
    - Иначе возвращаем DEFAULT_MIN_CTR.

    Это намеренно простая реализация — при необходимости можно расширить с запросами в ClickHouse/Redis.
    """
    try:
        hard_min = getattr(adv, "hard_min_ctr", None)
        if hard_min:
            return float(hard_min)
    except Exception:
        pass
    return float(DEFAULT_MIN_CTR)
