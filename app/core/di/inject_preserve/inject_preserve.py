__all__ = ["inject"]

import inspect
from functools import wraps
from typing import Callable

from dependency_injector.wiring import inject as original_inject


def inject(fn) -> Callable:
    injected = original_inject(fn)

    # копируем метаданные функции
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return injected(*args, **kwargs)

    # явно устанавливаем правильную сигнатуру
    wrapper.__signature__ = inspect.signature(fn)
    return wrapper
