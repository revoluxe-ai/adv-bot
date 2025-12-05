from collections.abc import Awaitable
from typing import Any

from .models import AdvPayment

__all__ = ["process_payment_for_advs", "AdvPayment"]


# TODO: убрать эту обёртку, когда решится проблема циклического импорта между Pricer и wildberries.models
# пока это быстрый костыль.


def process_payment_for_advs(*args: Any, **kwargs: Any) -> Awaitable[None]:
    """Ленивая обёртка для избежания циклического импорта.

    Импортируем фактическую реализацию только при вызове,
    чтобы не тянуть зависимости (Pricer -> wildberries.models) во время инициализации пакета.
    """
    from .billing import process_payment_for_advs as _impl

    return _impl(*args, **kwargs)
