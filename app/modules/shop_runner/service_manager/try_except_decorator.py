"""Минимальная заглушка декоратора try_except_decorator для прогонов.

Это облегченная реализация, которая просто возвращает оригинальную функцию
без изменения поведения. Используется для совместимости во время прогонов,
когда реальная логика повторных попыток не требуется.
"""

from collections.abc import Callable, Coroutine
from typing import Any


def try_except_decorator(func: Callable[..., Coroutine[Any, Any, Any]] | None = None):
    def decorator(f: Callable[..., Coroutine[Any, Any, Any]]):
        async def wrapper(*args: Any, **kwargs: Any):
            return await f(*args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    return decorator(func)
